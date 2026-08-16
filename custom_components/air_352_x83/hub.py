"""Runtime hub for 352 X83-family purifiers."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import socket

from .const import (
    COMMANDS,
    CONTROL_MODELS,
    UDP_PORT,
    X50_FAMILY_MODELS,
    X83_FAMILY_MODELS,
)
from .protocol import (
    assemble_discovery_packet,
    assemble_inner_packet,
    assemble_packet,
    build_f072_command,
    parse_discovery_response,
    parse_x50_state,
    parse_x83_state,
)

_LOGGER = logging.getLogger(__name__)


class X83Hub:
    """Coordinate UDP state and commands for one purifier."""

    def __init__(self, hass, host, mac, model):
        self.hass = hass
        self.host = host
        self.mac = mac.replace(":", "").replace("-", "").upper()
        self.model = model
        # Status packets replace this value before normal controls are sent.
        self.company_code = 0xF1
        self.auth_code = 0x0403 if model == "x83c" else 0x0504
        self.current_seq = 0
        self.last_seen = 0
        self.command_lock = 0
        self._control_lock = asyncio.Lock()
        self.status = {
            "pm25": 0,
            "speed": 0,
            "power": "OFF",
            "light": True,
            "mode": None,
            "filter_installed": "未安装",
            "total_air": 0,
            "total_purification": 0,
            "timer_hours": 0,
            "timer_remaining_minutes": 0,
            "air_quality_level": None,
            "child_lock": False,
            "ptc": None,
            "online": False,
        }
        self._callbacks = set()

    def register_callback(self, callback):
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        self._callbacks.discard(callback)

    def _assemble(self, seq, command):
        if self.model in X50_FAMILY_MODELS:
            command_id, value = command
            return assemble_inner_packet(
                self.mac,
                self.model,
                seq,
                build_f072_command(seq, command_id, value),
                company_code=self.company_code,
                auth_code=self.auth_code,
            )
        return assemble_packet(
            self.mac,
            self.model,
            seq,
            command,
            company_code=self.company_code,
            auth_code=self.auth_code,
        )

    def _resolve_command(self, action):
        """Map a Home Assistant action to its model-specific wire value."""
        if self.model in X83_FAMILY_MODELS:
            return COMMANDS.get(action)

        # APK-derived X50 values. These have not been hardware-validated.
        common = {
            "on": (0x5E, 0x00),
            "off": (0x5E, 0x11),
            "light_on": (0x56, 0x00),
            "light_off": (0x56, 0x11),
            "auto": (0x51, 0x01),
            "sleep": (0x51, 0x02),
            "turbo": (0x51, 0x03),
            "purify": (0x51, 0x05),
            "timer_off": (0x54, 0x00),
            "timer_1h": (0x54, 0x01),
            "timer_2h": (0x54, 0x02),
            "timer_3h": (0x54, 0x03),
            "timer_5h": (0x54, 0x05),
            "timer_8h": (0x54, 0x08),
            "child_lock_on": (0x55, 0x00),
            "child_lock_off": (0x55, 0x11),
            "query": (0x11, 0x11),
        }
        if action in common:
            return common[action]
        if action.startswith("speed_"):
            speed = int(action.removeprefix("speed_"))
            values = (0x01, 0x02, 0x03, 0x04, 0x05, 0x00)
            if 1 <= speed <= len(values):
                return (0x52, values[speed - 1])
        if action.startswith("ptc_"):
            value = int(action.removeprefix("ptc_"))
            if value in (0, 1, 2):
                return (0x53, value)
        return None

    async def async_control(self, action):
        """Send one model-specific action."""
        if self.model not in CONTROL_MODELS:
            raise ValueError(
                f"Control protocol is not implemented for model {self.model}"
            )

        async with self._control_lock:
            now = datetime.now().timestamp()
            self.command_lock = now + 3.0

            if (now - self.last_seen) > 20:
                await self._async_wakeup()
                await asyncio.sleep(0.5)

            command = self._resolve_command(action)
            if command is None:
                raise ValueError(f"Unsupported purifier action: {action}")

            self.current_seq = (self.current_seq + 1) & 0xFFFF
            await self._async_send(self._assemble(self.current_seq, command))

    async def _async_wakeup(self):
        discovery = assemble_discovery_packet(
            self.mac, self.model, sequence=self.current_seq
        )
        # The packet already targets one MAC; avoid probing unrelated hosts.
        await self._async_send(discovery)

    async def _async_send(self, packet):
        def _send():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(packet, (self.host, UDP_PORT))

        await asyncio.get_running_loop().run_in_executor(None, _send)

    def parse_data(self, data, addr=None):
        """Accept a state packet belonging to this configured device."""
        discovery = parse_discovery_response(data)
        if discovery is not None:
            if str(discovery["mac"]) != self.mac:
                return
            if addr is not None and addr[0] != self.host:
                return
            self.company_code = int(discovery["company_code"])
            self.auth_code = int(discovery["auth_code"])
            return

        if len(data) < 30 or data[0] != 0xA1:
            return
        if data[2:8] != bytes.fromhex(self.mac):
            return
        if addr is not None and addr[0] != self.host:
            return

        device_type = data[13]
        if device_type == 0x02:
            # X83C shares type 02 with X83; never downgrade explicit identity.
            if self.model not in X83_FAMILY_MODELS:
                return
            parser = parse_x83_state
        elif device_type == 0x03 and self.model == "x50":
            parser = parse_x50_state
        else:
            return

        received_seq = int.from_bytes(data[10:12], "big")
        if received_seq:
            delta = (received_seq - self.current_seq) & 0xFFFF
            if self.current_seq == 0 or delta < 0x8000:
                self.current_seq = received_seq

        self.auth_code = int.from_bytes(data[14:16], "big")
        self.company_code = data[12]
        now = datetime.now().timestamp()
        self.last_seen = now

        try:
            parsed = parser(data)
            if not parsed:
                return

            # During an optimistic update, discard only stale broadcasts. A
            # response echoing the current request sequence is authoritative.
            is_stale_while_locked = (
                now < self.command_lock and received_seq != self.current_seq
            )
            if is_stale_while_locked:
                parsed.pop("power", None)
                parsed.pop("speed", None)
                parsed.pop("mode", None)

            self.status.update(parsed)
            self.status["online"] = True
        except (IndexError, TypeError, ValueError):
            _LOGGER.debug("忽略无法解析的净化器状态包", exc_info=True)
            return

        for callback in self._callbacks:
            callback()

import asyncio
import logging
import socket
from time import time

from .const import (
    COMMANDS,
    CONTROL_MODELS,
    G30_FAMILY_MODELS,
    UDP_PORT,
    X50_FAMILY_MODELS,
    X83_FAMILY_MODELS,
)
from .protocol import (
    assemble_discovery_packet,
    assemble_inner_packet,
    assemble_packet,
    build_f072_command,
    build_m25_command,
    parse_discovery_response,
    parse_f072_state,
    parse_m25_state,
    parse_x83_state,
)

_LOGGER = logging.getLogger(__name__)

class X83Hub:
    def __init__(self, hass, host, mac, model, company_code=None, auth_code=None):
        self.hass = hass
        self.host = host
        self.mac = mac.replace(":", "").upper()
        self.model = model
        self.device_name = (
            "352 M25 空气检测仪"
            if model == "m25"
            else f"352 {model.upper()} 空气净化器"
        )
        # X83/X50 commonly use 0x0504. X83C broadcasts its actual device auth
        # code in every status packet, so parse_data replaces this value before
        # normal control commands are sent.
        self.company_code = 0xF1 if company_code is None else int(company_code)
        self.auth_code = (
            (0x0403 if model == "x83c" else 0x0504)
            if auth_code is None
            else int(auth_code)
        )
        self.current_seq = 0
        self.last_seen = 0
        self.command_lock = 0
        self._control_lock = asyncio.Lock()
        self.status = {
            "pm25": 0, "speed": 0, "power": "OFF", "light": True, "mode": "None",
            "filter_type": None, "total_air": 0,
            "total_purification": 0, "timer_hours": 0,
            "timer_remaining_minutes": 0, "air_quality_level": None,
            "child_lock": False, "temperature": None, "humidity": None,
            "co2": None, "ptc": None, "air_volume": None,
            "linkage_state": None, "backlight": None, "mode_code": None,
            "online": False
        }
        self._callbacks = set()

    def register_callback(self, callback):
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        self._callbacks.discard(callback)

    def _assemble(self, seq, command):
        if self.model in X50_FAMILY_MODELS or self.model in G30_FAMILY_MODELS:
            command_id, value, value_16bit = command
            inner = build_f072_command(
                0x04 if self.model in G30_FAMILY_MODELS else 0x03,
                seq,
                command_id,
                value,
                value_16bit=value_16bit,
            )
            return assemble_inner_packet(
                self.mac,
                self.model,
                seq,
                inner,
                company_code=self.company_code,
                auth_code=self.auth_code,
            )
        if self.model == "m25":
            return assemble_inner_packet(
                self.mac,
                self.model,
                seq,
                build_m25_command(command),
                route=0x03,
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
        if self.model in X83_FAMILY_MODELS:
            return COMMANDS.get(action)

        if self.model == "m25":
            return (
                action
                if action
                in {"query", "backlight_query", "light_on", "light_off"}
                else None
            )

        common = {
            "on": (0x5E, 0x00, False),
            "off": (0x5E, 0x11, False),
            "light_on": (0x56, 0x00, False),
            "light_off": (0x56, 0x11, False),
            "auto": (0x51, 0x01, False),
            "sleep": (0x51, 0x02, False),
            "turbo": (0x51, 0x03, False),
            "manual": (0x51, 0x05, False),
            "purify": (0x51, 0x05, False),
            "timer_off": (0x54, 0x00, False),
            "timer_1h": (0x54, 0x01, False),
            "timer_2h": (0x54, 0x02, False),
            "timer_3h": (0x54, 0x03, False),
            "timer_5h": (0x54, 0x05, False),
            "timer_8h": (0x54, 0x08, False),
            "child_lock_on": (0x55, 0x00, False),
            "child_lock_off": (0x55, 0x11, False),
            "query": (0x11, 0x11, False),
        }
        if action in common:
            return common[action]
        if self.model in X50_FAMILY_MODELS and action.startswith("speed_"):
            speed = int(action.removeprefix("speed_"))
            values = (0x01, 0x02, 0x03, 0x04, 0x05, 0x00)
            if 1 <= speed <= len(values):
                return (0x52, values[speed - 1], False)
        if action.startswith("ptc_"):
            return (0x53, int(action.removeprefix("ptc_")), False)
        if self.model in G30_FAMILY_MODELS and action.startswith("air_volume_"):
            return (0x58, int(action.removeprefix("air_volume_")), True)
        return None

    async def async_control(self, action):
        if self.model not in CONTROL_MODELS:
            raise ValueError(
                f"Control protocol is not implemented for model {self.model}"
            )

        async with self._control_lock:
            now = time()
            self.command_lock = now + 3.0

            if (now - self.last_seen) > 20:
                await self._async_wakeup()
                await asyncio.sleep(0.5)

            command = self._resolve_command(action)
            if command is None:
                raise ValueError(f"Unsupported purifier action: {action}")

            # Periodic broadcasts often carry sequence 0000. Keep a local
            # monotonic sequence so consecutive controls are never duplicates.
            self.current_seq = (self.current_seq + 1) & 0xFFFF
            packet = self._assemble(self.current_seq, command)
            await self._async_send(packet)

            # The archived M25 app queries its detector data and backlight via
            # two separate commands. Keep them together behind HA's query.
            if self.model == "m25" and action == "query":
                self.current_seq = (self.current_seq + 1) & 0xFFFF
                await self._async_send(
                    self._assemble(self.current_seq, "backlight_query")
                )

    async def _async_wakeup(self):
        discovery = assemble_discovery_packet(
            self.mac, self.model, sequence=self.current_seq
        )
        # The packet already targets one MAC and the device accepts it by
        # unicast. Avoid waking or probing unrelated LAN hosts.
        await self._async_send(discovery)

    async def _async_send(self, packet, broadcast=False):
        def _send():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                if broadcast:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.sendto(packet, ("255.255.255.255", UDP_PORT))
                else:
                    s.sendto(packet, (self.host, UDP_PORT))
        await asyncio.get_running_loop().run_in_executor(None, _send)

    def parse_data(self, data, addr=None):
        discovery = parse_discovery_response(data)
        if discovery is not None:
            if str(discovery["mac"]) != self.mac:
                return
            self.company_code = int(discovery["company_code"])
            self.auth_code = int(discovery["auth_code"])
            return

        if self.model == "m25":
            if addr is not None and addr[0] != self.host:
                return
            if len(data) >= 16 and data[0] == 0xA1:
                if data[2:8] != bytes.fromhex(self.mac):
                    return
                self.company_code = data[12]
                self.auth_code = int.from_bytes(data[14:16], "big")
                received_seq = int.from_bytes(data[10:12], "big")
                if received_seq:
                    self.current_seq = received_seq
            parsed = parse_m25_state(data)
            if parsed:
                self.last_seen = time()
                self.status.update(parsed)
                self.status["online"] = True
                for callback in self._callbacks:
                    callback()
            return

        if len(data) < 30 or data[0] != 0xA1:
            return
        if data[2:8] != bytes.fromhex(self.mac):
            return
        
        received_seq = int.from_bytes(data[10:12], "big")
        if received_seq:
            delta = (received_seq - self.current_seq) & 0xFFFF
            if self.current_seq == 0 or delta < 0x8000:
                self.current_seq = received_seq
        self.auth_code = int.from_bytes(data[14:16], 'big')
        self.company_code = data[12]
        now = time()
        self.last_seen = now
        
        if data[13] == 2:
            # X83C uses the same outer device type as X83. Preserve an
            # explicitly configured X83C identity instead of downgrading it.
            if self.model not in X83_FAMILY_MODELS:
                self.model = "x83"
        elif data[13] == 3:
            if self.model not in X50_FAMILY_MODELS:
                self.model = "x50"
        elif data[13] == 4:
            if self.model not in G30_FAMILY_MODELS:
                self.model = "g30"
        else:
            return
            
        try:
            if data[13] == 2:
                parsed = parse_x83_state(data)
            elif data[13] == 4:
                parsed = parse_f072_state(data, g30_family=True)
            else:
                parsed = parse_f072_state(data)
            if not parsed:
                return
            # Ignore only stale broadcasts while an optimistic control update
            # is settling. A response that echoes the current command sequence
            # is authoritative and must be accepted immediately; otherwise a
            # speed/mode value can remain stale until the next periodic packet.
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

        for callback in self._callbacks:
            callback()

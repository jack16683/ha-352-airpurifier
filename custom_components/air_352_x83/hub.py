import asyncio
import socket
import logging
from datetime import datetime
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
    assemble_packet,
    parse_f072_state,
    parse_m25_state,
    parse_x83_state,
)

_LOGGER = logging.getLogger(__name__)

class X83Hub:
    def __init__(self, hass, host, mac, model):
        self.hass = hass
        self.host = host
        self.mac = mac.replace(":", "").upper()
        self.model = model
        # X83/X50 commonly use 0x0504. X83C broadcasts its actual device auth
        # code in every status packet, so parse_data replaces this value before
        # normal control commands are sent.
        self.auth_code = 0x0403 if model == "x83c" else 0x0504
        self.current_seq = 0
        self.last_seen = 0
        self.command_lock = 0
        self._control_lock = asyncio.Lock()
        self.status = {
            "pm25": 0, "speed": 0, "power": "OFF", "light": True, "mode": "None",
            "filter_installed": "未安装", "total_air": 0,
            "total_purification": 0, "timer_hours": 0,
            "timer_remaining_minutes": 0, "air_quality_level": None,
            "child_lock": False, "temperature": None, "humidity": None,
            "co2": None, "ptc": None, "air_volume": None,
            "linkage_state": None, "backlight": None, "online": False
        }
        self._callbacks = set()

    def register_callback(self, callback):
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        self._callbacks.discard(callback)

    def _assemble(self, seq, command):
        return assemble_packet(
            self.mac, self.model, seq, command, auth_code=self.auth_code
        )

    async def async_control(self, action):
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

            command = COMMANDS.get(action)
            if command is None:
                raise ValueError(f"Unsupported purifier action: {action}")

            # Periodic broadcasts often carry sequence 0000. Keep a local
            # monotonic sequence so consecutive controls are never duplicates.
            self.current_seq = (self.current_seq + 1) & 0xFFFF
            packet = self._assemble(self.current_seq, command)
            await self._async_send(packet)

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
        if self.model == "m25":
            if addr is not None and addr[0] != self.host:
                return
            parsed = parse_m25_state(data)
            if parsed:
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
        now = datetime.now().timestamp()
        self.last_seen = now
        
        if data[13] == 2:
            # X83C uses the same outer device type as X83. Preserve an
            # explicitly configured X83C identity instead of downgrading it.
            if self.model not in X83_FAMILY_MODELS:
                self.model = "x83"
            base = 16
        elif data[13] == 3:
            if self.model not in X50_FAMILY_MODELS:
                self.model = "x50"
            base = 24
        elif data[13] == 4:
            if self.model not in G30_FAMILY_MODELS:
                self.model = "g30"
            base = 24
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
            is_locked = now < self.command_lock
            if is_locked:
                parsed.pop("power", None)
                parsed.pop("speed", None)
                parsed.pop("mode", None)

            self.status.update(parsed)
            self.status["online"] = True
        except (IndexError, TypeError, ValueError):
            _LOGGER.debug("忽略无法解析的净化器状态包", exc_info=True)

        for callback in self._callbacks:
            callback()

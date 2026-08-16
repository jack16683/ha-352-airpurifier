"""Local UDP discovery for 352 air purifiers."""

from __future__ import annotations

import asyncio
import socket
from time import monotonic

from .const import UDP_PORT
from .protocol import assemble_discovery_packet, parse_discovery_response


async def async_discover_devices(
    candidates: list[tuple[str, str]], timeout: float = 2.0
) -> list[dict[str, object]]:
    """Probe DHCP candidates and return verified discovery responses."""
    if not candidates:
        return []

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass
    sock.setblocking(False)

    try:
        sock.bind(("0.0.0.0", UDP_PORT))
        expected_macs = {mac.upper() for _, mac in candidates}
        sequence = 1
        for host, mac in candidates:
            # One request per supported protocol type. X83/X83C share type 02.
            for model in ("x83c", "x50"):
                packet = assemble_discovery_packet(mac, model, sequence)
                sequence = (sequence + 1) & 0xFFFF
                await loop.sock_sendto(sock, packet, (host, UDP_PORT))

        found: dict[str, dict[str, object]] = {}
        deadline = monotonic() + timeout
        while (remaining := deadline - monotonic()) > 0:
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 512), timeout=remaining
                )
            except TimeoutError:
                break

            device = parse_discovery_response(data)
            if device is None or device["mac"] not in expected_macs:
                continue
            if device["host"] == "0.0.0.0":
                device["host"] = addr[0]
            found[str(device["mac"])] = device

        return list(found.values())
    finally:
        sock.close()

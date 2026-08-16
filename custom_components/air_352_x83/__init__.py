"""352 X83-family local integration."""

from __future__ import annotations

import asyncio
import logging
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONTROL_MODELS, DOMAIN, UDP_PORT
from .hub import X83Hub

_LOGGER = logging.getLogger(__name__)


def _platforms_for_model(model: str) -> list[str]:
    """Return only platforms whose protocol is implemented for the model."""
    if model in CONTROL_MODELS:
        return ["fan", "sensor", "select", "switch", "light"]
    return ["sensor"]


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Normalize legacy entries and enable reconfiguration."""
    if config_entry.version == 1:
        data = dict(config_entry.data)
        mac = data.get("mac")
        normalized_mac = None
        if mac:
            normalized_mac = mac.replace(":", "").replace("-", "").upper()
            data["mac"] = normalized_mac

        hass.config_entries.async_update_entry(
            config_entry,
            data=data,
            unique_id=normalized_mac or config_entry.unique_id,
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up one configured purifier."""
    host = entry.data["host"]
    mac = entry.data["mac"]
    model = entry.data.get("model", "x83")
    hub = X83Hub(hass, host, mac, model)

    # Speed now lives on the fan; timer and child lock are writable entities.
    registry = er.async_get(hass)
    for platform, unique_id in (
        ("sensor", f"sensor_{hub.mac}_speed"),
        ("sensor", f"sensor_{hub.mac}_timer_hours"),
        ("binary_sensor", f"binary_sensor_{hub.mac}_child_lock"),
    ):
        if entity_id := registry.async_get_entity_id(platform, DOMAIN, unique_id):
            registry.async_remove(entity_id)

    class X83Protocol(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            hub.parse_data(data, addr)

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass

    try:
        sock.bind(("0.0.0.0", UDP_PORT))
        transport, _ = await loop.create_datagram_endpoint(X83Protocol, sock=sock)
        hub.transport = transport
    except Exception as err:  # Home Assistant logs the concrete socket error.
        sock.close()
        _LOGGER.error("无法创建 UDP 监听: %s", err)
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    platforms = _platforms_for_model(model)
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # X50 uses its APK-derived F072/CRC-16 query; X83-family models use A5A0.
    if model in CONTROL_MODELS:
        entry.async_create_background_task(
            hass, hub.async_control("query"), "352 initial state query"
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload entities and close the UDP listener."""
    model = entry.data.get("model", "x83")
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for_model(model)
    )
    if unload_ok:
        hub = hass.data[DOMAIN].pop(entry.entry_id)
        if getattr(hub, "transport", None):
            hub.transport.close()
    return unload_ok

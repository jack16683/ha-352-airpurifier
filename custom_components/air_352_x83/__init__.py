import asyncio
import socket
import logging
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
    """Migrate legacy model data while preserving real X83 configurations."""
    if config_entry.version == 1:
        data = dict(config_entry.data)
        model = data.get("model", "x83")

        # This installation was originally configured as X83 because X83C was
        # not an available choice, then explicitly renamed to X83C in HA.
        if model == "x83" and "X83C" in config_entry.title.upper():
            data["model"] = "x83c"

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
    host = entry.data.get("host")
    mac = entry.data.get("mac")
    model = entry.data.get("model", "x83")
    
    hub = X83Hub(hass, host, mac, model)

    # Version 1.3 folds speed into the fan entity and replaces read-only timer
    # and child-lock entities with controls. Remove their obsolete registry
    # entries so HomeKit does not receive duplicate unavailable accessories.
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
    except AttributeError:
        pass
        
    try:
        sock.bind(('0.0.0.0', UDP_PORT))
    except OSError:
        pass

    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: X83Protocol(), sock=sock
        )
        hub.transport = transport
    except Exception as e:
        _LOGGER.error("无法创建 UDP 监听: %s", e)
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    platforms = _platforms_for_model(model)
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    

    # X50 uses an F072/CRC-16 command frame, not the X83-family A5A0 frame.
    # Keep its legacy passive state parser available without transmitting a
    # query until that protocol has hardware validation.
    if model in CONTROL_MODELS:
        hass.loop.create_task(hub.async_control("query"))
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    model = entry.data.get("model", "x83")
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for_model(model)
    )
    if unload_ok:
        hub = hass.data[DOMAIN].pop(entry.entry_id)
        if hasattr(hub, 'transport') and hub.transport:
            hub.transport.close()
    return unload_ok

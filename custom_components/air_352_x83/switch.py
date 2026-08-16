"""Switch settings for supported 352 purifiers."""

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([X83ChildLockSwitch(hub)])


class X83ChildLockSwitch(SwitchEntity):
    """Control and report the purifier's physical child lock."""

    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = "童锁"
        self._attr_unique_id = f"switch_{hub.mac}_child_lock"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._hub.mac)},
            "name": self._hub.device_name,
            "manufacturer": "352",
            "model": self._hub.model.upper(),
        }

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.async_write_ha_state)

    @property
    def is_on(self):
        return self._hub.status.get("child_lock", False)

    @property
    def icon(self):
        return "mdi:lock" if self.is_on else "mdi:lock-open-variant"

    async def async_turn_on(self, **kwargs):
        self._hub.status["child_lock"] = True
        self.async_write_ha_state()
        await self._hub.async_control("child_lock_on")

    async def async_turn_off(self, **kwargs):
        self._hub.status["child_lock"] = False
        self.async_write_ha_state()
        await self._hub.async_control("child_lock_off")

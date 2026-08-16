from homeassistant.components.light import ColorMode, LightEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([X83LightEntity(hub)])

class X83LightEntity(LightEntity):
    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = "背光" if hub.model == "m25" else "屏幕灯"
        self._attr_unique_id = f"light_{hub.mac}"
        self._attr_icon = "mdi:led-on"
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._hub.mac)},
            "name": self._hub.device_name,
            "manufacturer": "352",
            "model": self._hub.model.upper()
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
        if self._hub.model == "m25":
            return self._hub.status.get("backlight") == 1
        if self._hub.status.get("power") == "OFF":
            return False
        return self._hub.status.get("light", False)

    async def async_turn_on(self, **kwargs):
        self._hub.status["backlight" if self._hub.model == "m25" else "light"] = (
            1 if self._hub.model == "m25" else True
        )
        self.async_write_ha_state()
        await self._hub.async_control("light_on")

    async def async_turn_off(self, **kwargs):
        self._hub.status["backlight" if self._hub.model == "m25" else "light"] = (
            0 if self._hub.model == "m25" else False
        )
        self.async_write_ha_state()
        await self._hub.async_control("light_off")

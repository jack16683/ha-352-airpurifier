from homeassistant.components.fan import FanEntity, FanEntityFeature

from .const import (
    DOMAIN,
    G30_AIR_VOLUME_RANGE,
    G30_AIR_VOLUME_STEP,
    G30_FAMILY_MODELS,
    MODE_ACTION_BY_LABEL,
    MODE_LABELS,
    X50_FAMILY_MODELS,
    X83_FAMILY_MODELS,
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([X83FanEntity(hub)])

class X83FanEntity(FanEntity):
    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_unique_id = f"fan_{hub.mac}"
        
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | 
            FanEntityFeature.TURN_ON | 
            FanEntityFeature.TURN_OFF |
            FanEntityFeature.PRESET_MODE
        )
        if hub.model in G30_FAMILY_MODELS:
            minimum, maximum = G30_AIR_VOLUME_RANGE[hub.model]
            self._attr_speed_count = (
                (maximum - minimum) // G30_AIR_VOLUME_STEP + 1
            )
            self._preset_actions = ("auto", "purify")
        elif hub.model in X50_FAMILY_MODELS:
            self._attr_speed_count = 6
            self._preset_actions = ("auto", "sleep", "turbo", "purify")
        else:
            self._attr_speed_count = 6
            self._preset_actions = (
                "auto",
                "sleep",
                "turbo",
                "manual",
                "purify",
            )
        self._attr_preset_modes = [
            MODE_LABELS[action] for action in self._preset_actions
        ]

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
        return self._hub.status.get("power") == "ON"

    @property
    def percentage(self):
        if self._hub.model in G30_FAMILY_MODELS:
            minimum, maximum = G30_AIR_VOLUME_RANGE[self._hub.model]
            value = self._hub.status.get("air_volume")
            if not isinstance(value, int) or value <= 0:
                return 0
            return max(
                1,
                min(100, round((value - minimum) * 100 / (maximum - minimum))),
            )
        speed = self._hub.status.get("speed", 0)
        return int((speed / 6) * 100) if speed > 0 else 0

    @property
    def preset_mode(self):
        return MODE_LABELS.get(self._hub.status.get("mode"))

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        self._hub.status["power"] = "ON"
        self.async_write_ha_state()

        await self._hub.async_control("on")
        
        if percentage:
            await self.async_set_percentage(percentage)
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)

    async def async_turn_off(self, **kwargs):
        self._hub.status["power"] = "OFF"
        self.async_write_ha_state()

        await self._hub.async_control("off")

    async def async_set_percentage(self, percentage):
        if percentage == 0:
            await self.async_turn_off()
            return
            
        if self._hub.model in G30_FAMILY_MODELS:
            minimum, maximum = G30_AIR_VOLUME_RANGE[self._hub.model]
            unrounded = minimum + percentage * (maximum - minimum) / 100
            air_volume = (
                int((unrounded + G30_AIR_VOLUME_STEP / 2) // G30_AIR_VOLUME_STEP)
                * G30_AIR_VOLUME_STEP
            )
            air_volume = max(minimum, min(maximum, air_volume))
            self._hub.status["power"] = "ON"
            self._hub.status["air_volume"] = air_volume
            self.async_write_ha_state()
            await self._hub.async_control(f"air_volume_{air_volume}")
            return

        speed_idx = max(1, min(6, round((percentage / 100) * 6)))
        self._hub.status["power"] = "ON"
        self._hub.status["speed"] = speed_idx
        self.async_write_ha_state()

        await self._hub.async_control(f"speed_{speed_idx}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        # Keep accepting the former English actions for existing automations,
        # while advertising and reporting Chinese labels in Home Assistant.
        action = MODE_ACTION_BY_LABEL.get(preset_mode, preset_mode)
        if action in self._preset_actions:
            self._hub.status["power"] = "ON"
            self._hub.status["mode"] = action
            self.async_write_ha_state()

            if action == "manual" and self._hub.model in X83_FAMILY_MODELS:
                # X83C ignores the APK's 5105 mode command. A speed command is
                # the hardware-validated way to enter manual mode (status 04).
                speed = max(1, min(6, self._hub.status.get("speed", 1)))
                await self._hub.async_control(f"speed_{speed}")
            else:
                await self._hub.async_control(action)

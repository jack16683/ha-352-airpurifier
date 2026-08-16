"""Selectable settings for supported 352 purifiers."""

from homeassistant.components.select import SelectEntity

from .const import (
    DOMAIN,
    G30_FAMILY_MODELS,
    TIMER_OPTION_TO_ACTION,
    X50_FAMILY_MODELS,
)

PTC_OPTIONS = {"关闭": 0, "一级": 1, "二级": 2}


async def async_setup_entry(hass, config_entry, async_add_entities):
    hub = hass.data[DOMAIN][config_entry.entry_id]
    entities = [X83ShutdownTimerSelect(hub)]
    if hub.model in G30_FAMILY_MODELS or hub.model in X50_FAMILY_MODELS:
        entities.append(ExperimentalPtcSelect(hub))
    async_add_entities(entities)


class X83ShutdownTimerSelect(SelectEntity):
    """Select the purifier's hardware shutdown timer."""

    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = "关机定时"
        self._attr_icon = "mdi:timer-cog-outline"
        self._attr_unique_id = f"select_{hub.mac}_shutdown_timer"
        self._attr_options = list(TIMER_OPTION_TO_ACTION)

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
    def current_option(self):
        timer_hours = self._hub.status.get("timer_hours")
        for option, (hours, _) in TIMER_OPTION_TO_ACTION.items():
            if hours == timer_hours:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in TIMER_OPTION_TO_ACTION:
            raise ValueError(f"Unsupported shutdown timer option: {option}")

        hours, action = TIMER_OPTION_TO_ACTION[option]
        self._hub.status["timer_hours"] = hours
        self._hub.status["timer_remaining_minutes"] = hours * 60
        self.async_write_ha_state()
        await self._hub.async_control(action)


class ExperimentalPtcSelect(SelectEntity):
    """Expose the three PTC values passed by the archived application."""

    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = "PTC 辅热"
        self._attr_icon = "mdi:radiator"
        self._attr_unique_id = f"select_{hub.mac}_ptc"
        self._attr_options = list(PTC_OPTIONS)

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
    def current_option(self):
        value = self._hub.status.get("ptc")
        return next(
            (name for name, code in PTC_OPTIONS.items() if code == value), None
        )

    async def async_select_option(self, option: str) -> None:
        if option not in PTC_OPTIONS:
            raise ValueError(f"Unsupported PTC option: {option}")
        value = PTC_OPTIONS[option]
        self._hub.status["ptc"] = value
        self.async_write_ha_state()
        await self._hub.async_control(f"ptc_{value}")

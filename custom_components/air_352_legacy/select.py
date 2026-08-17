"""Selectable settings for supported 352 purifiers."""

from homeassistant.components.select import SelectEntity

from .const import (
    DOMAIN,
    G30_FAMILY_MODELS,
    TIMER_OPTION_TO_ACTION,
    X50_FAMILY_MODELS,
)

PTC_OPTIONS = {"off": 0, "level_1": 1, "level_2": 2}
PTC_OPTION_ALIASES = {"关闭": "off", "一级": "level_1", "二级": "level_2"}
M25_BACKLIGHT_OPTIONS = {
    "off_after_5_minutes": (0, "light_off"),
    "always_on": (1, "light_on"),
}
M25_BACKLIGHT_ALIASES = {
    "5 分钟后关闭": "off_after_5_minutes",
    "常亮": "always_on",
}
TIMER_OPTION_ALIASES = {
    "关闭": "off",
    "1 小时": "1_hour",
    "2 小时": "2_hours",
    "3 小时": "3_hours",
    "5 小时": "5_hours",
    "8 小时": "8_hours",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    hub = hass.data[DOMAIN][config_entry.entry_id]
    if hub.model == "m25":
        async_add_entities([M25BacklightModeSelect(hub)])
        return
    entities = [X83ShutdownTimerSelect(hub)]
    if hub.model in G30_FAMILY_MODELS or hub.model in X50_FAMILY_MODELS:
        entities.append(ExperimentalPtcSelect(hub))
    async_add_entities(entities)


class M25BacklightModeSelect(SelectEntity):
    """Select the two M25 backlight behaviours named by the APK."""

    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = "backlight_mode"
        self._attr_icon = "mdi:lightbulb-auto"
        self._attr_unique_id = f"select_{hub.mac}_backlight_mode"
        self._attr_options = list(M25_BACKLIGHT_OPTIONS)

    @property
    def device_info(self):
        return self._hub.device_info

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.async_write_ha_state)

    @property
    def current_option(self):
        value = self._hub.status.get("backlight")
        return next(
            (
                name
                for name, (code, _) in M25_BACKLIGHT_OPTIONS.items()
                if code == value
            ),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        option = M25_BACKLIGHT_ALIASES.get(option, option)
        if option not in M25_BACKLIGHT_OPTIONS:
            raise ValueError(f"Unsupported M25 backlight option: {option}")
        value, action = M25_BACKLIGHT_OPTIONS[option]
        self._hub.status["backlight"] = value
        self.async_write_ha_state()
        await self._hub.async_control(action)


class X83ShutdownTimerSelect(SelectEntity):
    """Select the purifier's hardware shutdown timer."""

    def __init__(self, hub):
        self._hub = hub
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = "shutdown_timer"
        self._attr_icon = "mdi:timer-cog-outline"
        self._attr_unique_id = f"select_{hub.mac}_shutdown_timer"
        self._attr_options = list(TIMER_OPTION_TO_ACTION)

    @property
    def device_info(self):
        return self._hub.device_info

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
        option = TIMER_OPTION_ALIASES.get(option, option)
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
        self._attr_name = None
        self._attr_translation_key = "ptc_heating"
        self._attr_icon = "mdi:radiator"
        self._attr_unique_id = f"select_{hub.mac}_ptc"
        self._attr_options = list(PTC_OPTIONS)

    @property
    def device_info(self):
        return self._hub.device_info

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
        option = PTC_OPTION_ALIASES.get(option, option)
        if option not in PTC_OPTIONS:
            raise ValueError(f"Unsupported PTC option: {option}")
        value = PTC_OPTIONS[option]
        self._hub.status["ptc"] = value
        self.async_write_ha_state()
        await self._hub.async_control(f"ptc_{value}")

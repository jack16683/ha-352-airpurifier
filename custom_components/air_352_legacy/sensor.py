from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, format_mac

from .const import (
    AIR_QUALITY_LABELS,
    CONTROL_MODELS,
    DOMAIN,
    G30_FAMILY_MODELS,
    MODE_CODE_LABELS,
)

POWER_STATE_LABELS = {"ON": "on", "OFF": "off"}
BOOLEAN_STATE_LABELS = {True: "on", False: "off"}


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    if hub.model == "m25":
        entities = [
            X83Sensor(hub, "pm25", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(hub, "linkage_state_raw", "linkage_state", None, "mdi:link"),
            X83Sensor(hub, "backlight_state_raw", "backlight", None, "mdi:lightbulb"),
        ]
    elif hub.model in G30_FAMILY_MODELS:
        entities = [
            X83Sensor(hub, "pm25", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(hub, "temperature", "temperature", "°C", "mdi:thermometer"),
            X83Sensor(hub, "humidity", "humidity", "%", "mdi:water-percent"),
            X83Sensor(hub, "carbon_dioxide", "co2", "ppm", "mdi:molecule-co2"),
            X83Sensor(hub, "ptc_state_raw", "ptc", None, "mdi:radiator"),
            X83Sensor(hub, "air_volume", "air_volume", None, "mdi:weather-windy"),
            X83Sensor(
                hub,
                "operating_mode",
                "mode_code",
                None,
                "mdi:fan-auto",
                value_map=MODE_CODE_LABELS,
            ),
            X83Sensor(
                hub,
                "power_state",
                "power",
                None,
                "mdi:power",
                value_map=POWER_STATE_LABELS,
            ),
            X83Sensor(
                hub,
                "display_state",
                "light",
                None,
                "mdi:led-on",
                value_map=BOOLEAN_STATE_LABELS,
            ),
            X83Sensor(
                hub,
                "child_lock_state",
                "child_lock",
                None,
                "mdi:lock",
                value_map=BOOLEAN_STATE_LABELS,
            ),
            X83Sensor(hub, "timer_setting", "timer_hours", "h", "mdi:timer"),
            X83Sensor(
                hub,
                "timer_remaining",
                "timer_remaining_minutes",
                "min",
                "mdi:timer-sand",
            ),
            X83Sensor(
                hub,
                "air_quality",
                "air_quality_level",
                None,
                "mdi:air-filter",
                value_map=AIR_QUALITY_LABELS,
            ),
            X83Sensor(
                hub,
                "filter_type_code",
                "filter_type",
                None,
                "mdi:filter-cog",
                unique_id_key="filter_installed",
            ),
            X83Sensor(
                hub, "current_run_air_volume", "total_air", "m³", "mdi:weather-windy"
            ),
            X83Sensor(
                hub,
                "lifetime_air_volume",
                "total_purification",
                "m³",
                "mdi:leaf-circle-outline",
            ),
        ]
    else:
        entities = [
            X83Sensor(hub, "pm25", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(
                hub,
                "lifetime_air_volume",
                "total_purification",
                "m³",
                "mdi:leaf-circle-outline",
            ),
            X83Sensor(
                hub,
                "filter_type_code",
                "filter_type",
                None,
                "mdi:filter-cog",
                unique_id_key="filter_installed",
            ),
            X83Sensor(
                hub,
                "timer_remaining",
                "timer_remaining_minutes",
                "min",
                "mdi:timer-sand",
            ),
            X83Sensor(
                hub,
                "air_quality",
                "air_quality_level",
                None,
                "mdi:air-filter",
                value_map=AIR_QUALITY_LABELS,
            ),
            X83Sensor(
                hub, "current_run_air_volume", "total_air", "m³", "mdi:weather-windy"
            ),
            X83Sensor(
                hub,
                "operating_mode",
                "mode_code",
                None,
                "mdi:fan-auto",
                value_map=MODE_CODE_LABELS,
            ),
            X83Sensor(
                hub, "linkage_state_raw", "linkage_state", None, "mdi:link"
            ),
        ]

        # Models without hardware-validated controls keep their statically
        # mapped settings as read-only diagnostics.
        if hub.model not in CONTROL_MODELS:
            entities.extend(
                [
                    X83Sensor(hub, "fan_speed_raw", "speed", None, "mdi:fan"),
                    X83Sensor(hub, "mode_state", "mode", None, "mdi:fan-auto"),
                    X83Sensor(
                        hub,
                        "power_state",
                        "power",
                        None,
                        "mdi:power",
                        value_map=POWER_STATE_LABELS,
                    ),
                    X83Sensor(
                        hub,
                        "display_state",
                        "light",
                        None,
                        "mdi:led-on",
                        value_map=BOOLEAN_STATE_LABELS,
                    ),
                    X83Sensor(hub, "timer_setting", "timer_hours", "h", "mdi:timer"),
                    X83Sensor(
                        hub,
                        "child_lock_state",
                        "child_lock",
                        None,
                        "mdi:lock",
                        value_map=BOOLEAN_STATE_LABELS,
                    ),
                ]
            )
    async_add_entities(entities)

class X83Sensor(SensorEntity):
    def __init__(
        self,
        hub,
        translation_key,
        key,
        unit,
        icon,
        unique_id_key=None,
        value_map=None,
    ):
        self._hub = hub
        self._key = key
        self._value_map = value_map
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = translation_key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_unique_id = f"sensor_{hub.mac}_{unique_id_key or key}"

    @property
    def device_info(self):
        return {
            **self._hub.device_info,
            "connections": {(CONNECTION_NETWORK_MAC, format_mac(self._hub.mac))},
        }

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.async_write_ha_state)

    @property
    def native_value(self):
        raw_value = self._hub.status.get(self._key)
        if raw_value is None:
            return None
        if self._value_map is None:
            return raw_value
        return self._value_map.get(raw_value, raw_value)

    @property
    def extra_state_attributes(self):
        if self._value_map is None:
            return None
        return {"raw_code": self._hub.status.get(self._key)}

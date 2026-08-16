from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, format_mac

from .const import (
    CONTROL_MODELS,
    DOMAIN,
    G30_FAMILY_MODELS,
)


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    if hub.model == "m25":
        entities = [
            X83Sensor(hub, "PM2.5", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(hub, "联动状态原始值", "linkage_state", None, "mdi:link"),
            X83Sensor(hub, "背光状态原始值", "backlight", None, "mdi:lightbulb"),
        ]
    elif hub.model in G30_FAMILY_MODELS:
        entities = [
            X83Sensor(hub, "PM2.5", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(hub, "温度", "temperature", "°C", "mdi:thermometer"),
            X83Sensor(hub, "湿度", "humidity", "%", "mdi:water-percent"),
            X83Sensor(hub, "二氧化碳", "co2", "ppm", "mdi:molecule-co2"),
            X83Sensor(hub, "PTC 状态原始值", "ptc", None, "mdi:radiator"),
            X83Sensor(hub, "风量", "air_volume", None, "mdi:weather-windy"),
            X83Sensor(hub, "模式原始值", "mode_code", None, "mdi:fan-auto"),
            X83Sensor(hub, "电源状态", "power", None, "mdi:power"),
            X83Sensor(hub, "屏幕状态", "light", None, "mdi:led-on"),
            X83Sensor(hub, "童锁状态", "child_lock", None, "mdi:lock"),
            X83Sensor(hub, "定时设置", "timer_hours", "h", "mdi:timer"),
            X83Sensor(
                hub,
                "定时剩余",
                "timer_remaining_minutes",
                "min",
                "mdi:timer-sand",
            ),
            X83Sensor(
                hub, "空气质量等级", "air_quality_level", None, "mdi:air-filter"
            ),
            X83Sensor(
                hub,
                "滤芯类型代码",
                "filter_type",
                None,
                "mdi:filter-cog",
                unique_id_key="filter_installed",
            ),
            X83Sensor(
                hub, "本次运行空气量", "total_air", "m³", "mdi:weather-windy"
            ),
            X83Sensor(
                hub,
                "设备累计空气量",
                "total_purification",
                "m³",
                "mdi:leaf-circle-outline",
            ),
        ]
    else:
        entities = [
            X83Sensor(hub, "PM2.5", "pm25", "µg/m³", "mdi:air-filter"),
            X83Sensor(
                hub,
                "设备累计空气量",
                "total_purification",
                "m³",
                "mdi:leaf-circle-outline",
            ),
            X83Sensor(
                hub,
                "滤芯类型代码",
                "filter_type",
                None,
                "mdi:filter-cog",
                unique_id_key="filter_installed",
            ),
            X83Sensor(
                hub,
                "定时剩余",
                "timer_remaining_minutes",
                "min",
                "mdi:timer-sand",
            ),
            X83Sensor(
                hub, "空气质量等级", "air_quality_level", None, "mdi:air-filter"
            ),
            X83Sensor(
                hub, "本次运行空气量", "total_air", "m³", "mdi:weather-windy"
            ),
            X83Sensor(hub, "模式代码", "mode_code", None, "mdi:fan-auto"),
            X83Sensor(
                hub, "联动状态原始值", "linkage_state", None, "mdi:link"
            ),
        ]

        # Models without hardware-validated controls keep their statically
        # mapped settings as read-only diagnostics.
        if hub.model not in CONTROL_MODELS:
            entities.extend(
                [
                    X83Sensor(hub, "风量档位原始值", "speed", None, "mdi:fan"),
                    X83Sensor(hub, "模式状态", "mode", None, "mdi:fan-auto"),
                    X83Sensor(hub, "电源状态", "power", None, "mdi:power"),
                    X83Sensor(hub, "屏幕状态", "light", None, "mdi:led-on"),
                    X83Sensor(hub, "定时设置", "timer_hours", "h", "mdi:timer"),
                    X83Sensor(hub, "童锁状态", "child_lock", None, "mdi:lock"),
                ]
            )
    async_add_entities(entities)

class X83Sensor(SensorEntity):
    def __init__(self, hub, name, key, unit, icon, unique_id_key=None):
        self._hub = hub
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_unique_id = f"sensor_{hub.mac}_{unique_id_key or key}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._hub.mac)},
            "connections": {(CONNECTION_NETWORK_MAC, format_mac(self._hub.mac))},
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
    def native_value(self):
        return self._hub.status.get(self._key)

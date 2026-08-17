"""Configuration flow for 352 air purifiers."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import DOMAIN, MODELS
from .discovery import async_discover_devices


def _normalize_mac(mac: str) -> str:
    return mac.replace(":", "").replace("-", "").upper()


def _model_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=list(MODELS),
            translation_key="model",
        )
    )


def _model_name(model: object) -> str:
    model_key = str(model)
    return MODELS.get(model_key, f"352 {model_key.upper()}")


class X83ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._discovered_devices: dict[str, dict[str, object]] = {}
        self._discovered_device: dict[str, object] | None = None

    @staticmethod
    def _normalize(user_input):
        data = {
            "model": user_input["model"],
            "host": user_input["host"],
            "mac": _normalize_mac(user_input["mac"]),
        }
        for key in ("company_code", "auth_code"):
            if key in user_input:
                data[key] = user_input[key]
        return data

    @staticmethod
    def _schema(defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    "model", default=defaults.get("model", "x83c")
                ): _model_selector(),
                vol.Required(
                    "host", default=defaults.get("host", "192.0.2.10")
                ): str,
                vol.Required(
                    "mac", default=defaults.get("mac", "")
                ): str,
            }
        )

    async def _async_create_device_entry(self, data):
        await self.async_set_unique_id(str(data["mac"]))
        self._abort_if_unique_id_configured(updates={"host": data["host"]})
        return self.async_create_entry(
            title=f"{_model_name(data['model'])} ({data['host']})",
            data=data,
        )

    async def async_step_user(self, user_input=None):
        """Offer automatic LAN discovery or the manual form."""
        return self.async_show_menu(
            step_id="user", menu_options=["automatic", "manual"]
        )

    async def async_step_automatic(self, user_input=None):
        """Probe 352 devices found by Home Assistant's DHCP inventory."""
        if user_input is not None:
            self._discovered_device = self._discovered_devices[user_input["device"]]
            return await self.async_step_discovery_confirm()

        candidates: dict[str, str] = {}
        configured = {str(value).upper() for value in self._async_current_ids()}
        # Home Assistant 2026.8+ provides a public DHCP-cache API. Keep the
        # older cache access as a compatibility fallback for 2026.7 and below.
        get_discoveries = getattr(dhcp, "async_discovered_service_info", None)
        if get_discoveries is not None:
            for info in get_discoveries(self.hass):
                mac = _normalize_mac(info.macaddress)
                if mac.startswith("009569") and mac not in configured:
                    candidates[mac] = info.ip
        else:
            dhcp_data = self.hass.data.get(dhcp.DATA_DHCP)
            address_data = dhcp_data.address_data if dhcp_data is not None else {}
            for mac_address, info in address_data.items():
                mac = _normalize_mac(mac_address)
                if mac.startswith("009569") and mac not in configured:
                    candidates[mac] = info[dhcp.IP_ADDRESS]

        devices = await async_discover_devices(
            [(host, mac) for mac, host in candidates.items()]
        )
        self._discovered_devices = {str(device["mac"]): device for device in devices}
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        labels = {
            mac: f"{_model_name(device['model'])} — {device['host']}"
            for mac, device in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="automatic",
            data_schema=vol.Schema({vol.Required("device"): vol.In(labels)}),
        )

    async def async_step_manual(self, user_input=None):
        """Keep the original manual IP/model/MAC configuration path."""
        if user_input is not None:
            return await self._async_create_device_entry(self._normalize(user_input))
        return self.async_show_form(step_id="manual", data_schema=self._schema())

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo):
        """Verify an OUI match using the purifier's own UDP response."""
        mac = _normalize_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={"host": discovery_info.ip})

        devices = await async_discover_devices([(discovery_info.ip, mac)])
        if not devices:
            return self.async_abort(reason="cannot_connect")
        self._discovered_device = devices[0]
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None):
        """Confirm discovery and allow overriding the inferred product model."""
        assert self._discovered_device is not None
        if user_input is not None:
            data = {
                "model": user_input["model"],
                "host": str(self._discovered_device["host"]),
                "mac": str(self._discovered_device["mac"]),
                "company_code": int(self._discovered_device["company_code"]),
                "auth_code": int(self._discovered_device["auth_code"]),
            }
            return await self._async_create_device_entry(data)

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "model", default=str(self._discovered_device["model"])
                    ): _model_selector()
                }
            ),
            description_placeholders={
                "host": str(self._discovered_device["host"]),
                "mac": str(self._discovered_device["mac"]),
            },
        )

    async def async_step_reconfigure(self, user_input=None):
        """Allow changing the model or address without recreating entities."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            data = self._normalize(user_input)
            for key in ("company_code", "auth_code"):
                if key in entry.data:
                    data[key] = entry.data[key]
            await self.async_set_unique_id(data["mac"])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(
            step_id="reconfigure", data_schema=self._schema(entry.data)
        )

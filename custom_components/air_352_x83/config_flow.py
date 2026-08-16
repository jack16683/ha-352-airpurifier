"""Configuration flow for 352 air purifiers."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import DOMAIN, MODELS
from .discovery import async_discover_devices


def _normalize_mac(mac: str) -> str:
    return mac.replace(":", "").replace("-", "").upper()


class X83ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._discovered_devices: dict[str, dict[str, object]] = {}
        self._discovered_device: dict[str, object] | None = None

    @staticmethod
    def _normalize(user_input):
        return {
            "model": user_input["model"],
            "host": user_input["host"],
            "mac": _normalize_mac(user_input["mac"]),
        }

    @staticmethod
    def _schema(defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    "model", default=defaults.get("model", "x83c")
                ): vol.In(MODELS),
                vol.Required(
                    "host", default=defaults.get("host", "192.168.50.18")
                ): str,
                vol.Required(
                    "mac", default=defaults.get("mac", "00:11:22:33:44:55")
                ): str,
            }
        )

    async def _async_create_device_entry(self, data):
        await self.async_set_unique_id(str(data["mac"]))
        self._abort_if_unique_id_configured(updates={"host": data["host"]})
        return self.async_create_entry(
            title=f"352 {str(data['model']).upper()} ({data['host']})", data=data
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

        candidates = []
        configured = {str(value).upper() for value in self._async_current_ids()}
        # DHCP keeps its latest address inventory in memory. There is no
        # public active scan API for config flows, so use that inventory only
        # to obtain candidates, then verify each one with the purifier's own
        # read-only discovery response before showing it to the user.
        dhcp_data = self.hass.data.get(dhcp.DATA_DHCP)
        address_data = dhcp_data.address_data if dhcp_data is not None else {}
        for mac_address, info in address_data.items():
            mac = _normalize_mac(mac_address)
            if mac.startswith("009569") and mac not in configured:
                candidates.append((info[dhcp.IP_ADDRESS], mac))

        devices = await async_discover_devices(candidates)
        self._discovered_devices = {str(device["mac"]): device for device in devices}
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        labels = {
            mac: f"352 {str(device['model']).upper()} — {device['host']}"
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
            }
            return await self._async_create_device_entry(data)

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "model", default=str(self._discovered_device["model"])
                    ): vol.In(MODELS)
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
            await self.async_set_unique_id(data["mac"])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(
            step_id="reconfigure", data_schema=self._schema(entry.data)
        )

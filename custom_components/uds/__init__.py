"""User-Defined Device Sensors integration."""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_ATTRIBUTES,
    SERVICE_SET_ATTRIBUTE_VALUE,
    SERVICE_CREATE_ATTRIBUTE,
    SERVICE_DELETE_ATTRIBUTE,
    SERVICE_RELOAD,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


def slugify_attribute(name: str) -> str:
    """Convert an attribute name to a safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_ATTRIBUTE_VALUE):
        return

    async def handle_set_attribute_value(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        attribute_key: str = call.data["attribute_key"]
        value: str = call.data["value"]

        for entry in hass.config_entries.async_entries(DOMAIN):
            new_data = copy.deepcopy(dict(entry.data))
            devices = new_data.get("devices") or dict(entry.options).get("devices") or {}
            if device_id in devices and attribute_key in devices[device_id].get("attributes", {}):
                devices[device_id]["attributes"][attribute_key]["value"] = value
                new_data["devices"] = devices
                hass.config_entries.async_update_entry(entry, data=new_data)
                await hass.config_entries.async_reload(entry.entry_id)
                return

        _LOGGER.warning("UDS set_attribute_value: device %s / key %s not found", device_id, attribute_key)

    async def handle_create_attribute(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        name: str = call.data["name"]
        value: str = call.data["value"]
        icon: str | None = call.data.get("icon")
        unit: str | None = call.data.get("unit_of_measurement")
        device_class: str | None = call.data.get("device_class")
        state_class: str | None = call.data.get("state_class")

        key = slugify_attribute(name)

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        device_name = device.name_by_user or device.name if device else device_id

        for entry in hass.config_entries.async_entries(DOMAIN):
            new_data = copy.deepcopy(dict(entry.data))
            devices = new_data.get("devices") or dict(entry.options).get("devices") or {}
            if device_id not in devices:
                devices[device_id] = {"device_name": device_name, "attributes": {}}
            devices[device_id]["attributes"][key] = {
                "name": name,
                "value": value,
                "icon": icon,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": state_class,
            }
            new_data["devices"] = devices
            hass.config_entries.async_update_entry(entry, data=new_data)
            await hass.config_entries.async_reload(entry.entry_id)
            return

        _LOGGER.warning("UDS create_attribute: no config entry found")

    async def handle_delete_attribute(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        attribute_key: str = call.data["attribute_key"]

        for entry in hass.config_entries.async_entries(DOMAIN):
            new_data = copy.deepcopy(dict(entry.data))
            devices = new_data.get("devices") or dict(entry.options).get("devices") or {}
            if device_id in devices and attribute_key in devices[device_id].get("attributes", {}):
                del devices[device_id]["attributes"][attribute_key]
                if not devices[device_id]["attributes"]:
                    del devices[device_id]
                new_data["devices"] = devices
                hass.config_entries.async_update_entry(entry, data=new_data)
                await hass.config_entries.async_reload(entry.entry_id)
                return

        _LOGGER.warning("UDS delete_attribute: device %s / key %s not found", device_id, attribute_key)

    async def handle_reload(call: ServiceCall) -> None:
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ATTRIBUTE_VALUE,
        handle_set_attribute_value,
        schema=vol.Schema({
            vol.Required("device_id"): cv.string,
            vol.Required("attribute_key"): cv.string,
            vol.Required("value"): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_ATTRIBUTE,
        handle_create_attribute,
        schema=vol.Schema({
            vol.Required("device_id"): cv.string,
            vol.Required("name"): cv.string,
            vol.Required("value"): cv.string,
            vol.Optional("icon"): cv.string,
            vol.Optional("unit_of_measurement"): cv.string,
            vol.Optional("device_class"): cv.string,
            vol.Optional("state_class"): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ATTRIBUTE,
        handle_delete_attribute,
        schema=vol.Schema({
            vol.Required("device_id"): cv.string,
            vol.Required("attribute_key"): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD,
        handle_reload,
        schema=vol.Schema({}),
    )

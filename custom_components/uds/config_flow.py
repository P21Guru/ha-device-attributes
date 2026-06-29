"""Config flow for User-Defined Device Sensors."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import DOMAIN


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _device_name(device: dr.DeviceEntry) -> str:
    return device.name_by_user or device.name or device.id


ATTRIBUTE_SCHEMA = vol.Schema({
    vol.Required("attribute_name"): selector.selector({"text": {}}),
    vol.Required("attribute_value"): selector.selector({"text": {}}),
    vol.Optional("icon"): selector.selector({"icon": {"placeholder": "mdi:label"}}),
    vol.Optional("unit_of_measurement"): selector.selector({"text": {}}),
    vol.Optional("device_class"): selector.selector({"text": {}}),
    vol.Optional("state_class"): selector.selector({"select": {
        "options": ["", "measurement", "total", "total_increasing"],
    }}),
    vol.Optional("notes"): selector.selector({"text": {"multiline": True}}),
})


class UDSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._selected_device_id: str | None = None
        self._selected_device_name: str | None = None
        self._pending_attributes: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: select a device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_device_id = user_input["device_id"]
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get(self._selected_device_id)
            self._selected_device_name = _device_name(device) if device else self._selected_device_id
            return await self.async_step_add_attribute()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_id"): selector.selector({"device": {}}),
            }),
            errors=errors,
        )

    async def async_step_add_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: add one or more attributes."""
        errors: dict[str, str] = {}

        if user_input is not None:
            attr_name = user_input["attribute_name"].strip()
            attr_key = _slugify(attr_name)

            if not attr_key:
                errors["attribute_name"] = "invalid_name"
            else:
                self._pending_attributes[attr_key] = {
                    "name": attr_name,
                    "value": user_input["attribute_value"],
                    "icon": user_input.get("icon"),
                    "unit_of_measurement": user_input.get("unit_of_measurement") or None,
                    "device_class": user_input.get("device_class") or None,
                    "state_class": user_input.get("state_class") or None,
                    "notes": user_input.get("notes") or None,
                }

                if user_input.get("add_another"):
                    return await self.async_step_add_attribute()

                return self._create_entry()

        schema = vol.Schema({
            vol.Required("attribute_name"): selector.selector({"text": {}}),
            vol.Required("attribute_value"): selector.selector({"text": {}}),
            vol.Optional("icon"): selector.selector({"icon": {"placeholder": "mdi:label"}}),
            vol.Optional("unit_of_measurement"): selector.selector({"text": {}}),
            vol.Optional("device_class"): selector.selector({"text": {}}),
            vol.Optional("state_class"): selector.selector({"select": {
                "options": [
                    {"value": "", "label": "None"},
                    {"value": "measurement", "label": "Measurement"},
                    {"value": "total", "label": "Total"},
                    {"value": "total_increasing", "label": "Total Increasing"},
                ],
            }}),
            vol.Optional("notes"): selector.selector({"text": {"multiline": True}}),
            vol.Optional("add_another", default=False): selector.selector({"boolean": {}}),
        })

        return self.async_show_form(
            step_id="add_attribute",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": self._selected_device_name or "",
            },
        )

    def _create_entry(self) -> config_entries.FlowResult:
        title = f"UDS – {self._selected_device_name}"
        return self.async_create_entry(
            title=title,
            data={
                "device_id": self._selected_device_id,
                "device_name": self._selected_device_name,
            },
            options={
                "devices": {
                    self._selected_device_id: {
                        "device_name": self._selected_device_name,
                        "attributes": self._pending_attributes,
                    }
                }
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "UDSOptionsFlow":
        return UDSOptionsFlow(config_entry)


class UDSOptionsFlow(config_entries.OptionsFlow):
    """Handle the options flow for editing/deleting attributes."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._devices: dict[str, Any] = {}
        self._selected_device_id: str | None = None
        self._selected_attr_key: str | None = None
        self._action: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Choose action."""
        if user_input is not None:
            self._action = user_input["action"]
            if self._action == "add_device":
                return await self.async_step_add_device()
            return await self.async_step_select_device()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action"): selector.selector({"select": {
                    "options": [
                        {"value": "add_device", "label": "Add attributes for a new device"},
                        {"value": "manage", "label": "Edit or delete existing attributes"},
                    ],
                }}),
            }),
        )

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Select a new device to add attributes for."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_device_id = user_input["device_id"]
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get(self._selected_device_id)
            device_name = _device_name(device) if device else self._selected_device_id

            options = dict(self._config_entry.options)
            devices = dict(options.get("devices", {}))
            if self._selected_device_id not in devices:
                devices[self._selected_device_id] = {
                    "device_name": device_name,
                    "attributes": {},
                }
            options["devices"] = devices
            self._devices = devices
            return await self.async_step_add_attribute()

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): selector.selector({"device": {}}),
            }),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Choose which device to manage."""
        options = dict(self._config_entry.options)
        self._devices = dict(options.get("devices", {}))

        if not self._devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            self._selected_device_id = user_input["device_id"]
            return await self.async_step_select_attribute()

        device_options = [
            {"value": did, "label": ddata.get("device_name", did)}
            for did, ddata in self._devices.items()
        ]

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): selector.selector({"select": {
                    "options": device_options,
                }}),
            }),
        )

    async def async_step_select_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Choose which attribute to manage and what to do with it."""
        device_data = self._devices.get(self._selected_device_id, {})
        attributes = device_data.get("attributes", {})

        if not attributes:
            return self.async_abort(reason="no_attributes")

        if user_input is not None:
            self._selected_attr_key = user_input["attribute_key"]
            action = user_input["attribute_action"]
            if action == "edit":
                return await self.async_step_edit_attribute()
            elif action == "delete":
                return await self.async_step_confirm_delete()
            elif action == "add_new":
                return await self.async_step_add_attribute()

        attr_options = [
            {"value": key, "label": data.get("name", key)}
            for key, data in attributes.items()
        ]
        attr_options.append({"value": "__new__", "label": "+ Add new attribute"})

        return self.async_show_form(
            step_id="select_attribute",
            data_schema=vol.Schema({
                vol.Required("attribute_key"): selector.selector({"select": {
                    "options": attr_options,
                }}),
                vol.Required("attribute_action", default="edit"): selector.selector({"select": {
                    "options": [
                        {"value": "edit", "label": "Edit"},
                        {"value": "delete", "label": "Delete"},
                        {"value": "add_new", "label": "Add new attribute"},
                    ],
                }}),
            }),
        )

    async def async_step_add_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new attribute to the selected device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            attr_name = user_input["attribute_name"].strip()
            attr_key = _slugify(attr_name)

            if not attr_key:
                errors["attribute_name"] = "invalid_name"
            else:
                options = dict(self._config_entry.options)
                devices = dict(options.get("devices", {}))
                if self._selected_device_id not in devices:
                    dev_reg = dr.async_get(self.hass)
                    device = dev_reg.async_get(self._selected_device_id)
                    device_name = _device_name(device) if device else self._selected_device_id
                    devices[self._selected_device_id] = {"device_name": device_name, "attributes": {}}

                devices[self._selected_device_id]["attributes"][attr_key] = {
                    "name": attr_name,
                    "value": user_input["attribute_value"],
                    "icon": user_input.get("icon"),
                    "unit_of_measurement": user_input.get("unit_of_measurement") or None,
                    "device_class": user_input.get("device_class") or None,
                    "state_class": user_input.get("state_class") or None,
                    "notes": user_input.get("notes") or None,
                }
                options["devices"] = devices
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema({
            vol.Required("attribute_name"): selector.selector({"text": {}}),
            vol.Required("attribute_value"): selector.selector({"text": {}}),
            vol.Optional("icon"): selector.selector({"icon": {"placeholder": "mdi:label"}}),
            vol.Optional("unit_of_measurement"): selector.selector({"text": {}}),
            vol.Optional("device_class"): selector.selector({"text": {}}),
            vol.Optional("state_class"): selector.selector({"select": {
                "options": [
                    {"value": "", "label": "None"},
                    {"value": "measurement", "label": "Measurement"},
                    {"value": "total", "label": "Total"},
                    {"value": "total_increasing", "label": "Total Increasing"},
                ],
            }}),
            vol.Optional("notes"): selector.selector({"text": {"multiline": True}}),
        })

        return self.async_show_form(
            step_id="add_attribute",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit an existing attribute."""
        errors: dict[str, str] = {}
        device_data = self._devices.get(self._selected_device_id, {})
        existing = device_data.get("attributes", {}).get(self._selected_attr_key, {})

        if user_input is not None:
            attr_name = user_input["attribute_name"].strip()
            if not _slugify(attr_name):
                errors["attribute_name"] = "invalid_name"
            else:
                options = dict(self._config_entry.options)
                devices = dict(options.get("devices", {}))
                devices[self._selected_device_id]["attributes"][self._selected_attr_key] = {
                    "name": attr_name,
                    "value": user_input["attribute_value"],
                    "icon": user_input.get("icon"),
                    "unit_of_measurement": user_input.get("unit_of_measurement") or None,
                    "device_class": user_input.get("device_class") or None,
                    "state_class": user_input.get("state_class") or None,
                    "notes": user_input.get("notes") or None,
                }
                options["devices"] = devices
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema({
            vol.Required("attribute_name", default=existing.get("name", "")): selector.selector({"text": {}}),
            vol.Required("attribute_value", default=existing.get("value", "")): selector.selector({"text": {}}),
            vol.Optional("icon", default=existing.get("icon") or ""): selector.selector({"icon": {"placeholder": "mdi:label"}}),
            vol.Optional("unit_of_measurement", default=existing.get("unit_of_measurement") or ""): selector.selector({"text": {}}),
            vol.Optional("device_class", default=existing.get("device_class") or ""): selector.selector({"text": {}}),
            vol.Optional("state_class", default=existing.get("state_class") or ""): selector.selector({"select": {
                "options": [
                    {"value": "", "label": "None"},
                    {"value": "measurement", "label": "Measurement"},
                    {"value": "total", "label": "Total"},
                    {"value": "total_increasing", "label": "Total Increasing"},
                ],
            }}),
            vol.Optional("notes", default=existing.get("notes") or ""): selector.selector({"text": {"multiline": True}}),
        })

        return self.async_show_form(
            step_id="edit_attribute",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "attribute_name": existing.get("name", self._selected_attr_key),
            },
        )

    async def async_step_confirm_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Confirm deletion of an attribute."""
        device_data = self._devices.get(self._selected_device_id, {})
        existing = device_data.get("attributes", {}).get(self._selected_attr_key, {})

        if user_input is not None:
            if user_input.get("confirm"):
                options = dict(self._config_entry.options)
                devices = dict(options.get("devices", {}))
                attrs = devices[self._selected_device_id]["attributes"]
                attrs.pop(self._selected_attr_key, None)
                if not attrs:
                    del devices[self._selected_device_id]
                options["devices"] = devices
                return self.async_create_entry(title="", data=options)
            return self.async_abort(reason="deletion_cancelled")

        return self.async_show_form(
            step_id="confirm_delete",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): selector.selector({"boolean": {}}),
            }),
            description_placeholders={
                "attribute_name": existing.get("name", self._selected_attr_key),
            },
        )

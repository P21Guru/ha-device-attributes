"""Sensor platform for User-Defined Device Sensors."""
from __future__ import annotations

import re
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_ATTRIBUTE_NAME,
    ATTR_ATTRIBUTE_KEY,
    ATTR_ATTRIBUTE_VALUE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_MANAGED,
    ATTR_DEVICE_MANUFACTURER,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_MODEL_ID,
    ATTR_DEVICE_SERIAL,
    ATTR_DEVICE_SW_VERSION,
    ATTR_DEVICE_HW_VERSION,
    ATTR_DEVICE_CONFIG_URL,
)

_LOGGER = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    options = config_entry.options
    devices_data: dict[str, Any] = options.get("devices", {})

    dev_reg = dr.async_get(hass)
    entities: list[UDSSensor] = []

    for device_id, device_data in devices_data.items():
        device_name = device_data.get("device_name", device_id)
        device_entry = dev_reg.async_get(device_id)

        for attr_key, attr_data in device_data.get("attributes", {}).items():
            entities.append(
                UDSSensor(
                    config_entry_id=config_entry.entry_id,
                    device_id=device_id,
                    device_name=device_name,
                    device_entry=device_entry,
                    attr_key=attr_key,
                    attr_data=attr_data,
                )
            )

    async_add_entities(entities)


def _dev_attr(device_entry: dr.DeviceEntry, field: str) -> str:
    """Safely read a DeviceEntry field that may not exist in older HA versions."""
    return getattr(device_entry, field, None) or "unavailable"


class UDSSensor(SensorEntity):
    """A sensor representing a single user-defined device attribute."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        config_entry_id: str,
        device_id: str,
        device_name: str,
        device_entry: dr.DeviceEntry | None,
        attr_key: str,
        attr_data: dict[str, Any],
    ) -> None:
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._device_name = device_name
        self._device_entry = device_entry
        self._attr_key = attr_key
        self._attr_data = attr_data

        device_slug = _slugify(device_name)
        self._attr_unique_id = f"uds_{device_id}_{attr_key}"
        self.entity_id = f"sensor.uds_{device_slug}_{attr_key}"
        self._attr_name = f"{device_name} {attr_data.get('name', attr_key)}"

        self._attr_native_value = attr_data.get("value") or None
        self._attr_icon = attr_data.get("icon") or None

        uom = attr_data.get("unit_of_measurement")
        self._attr_native_unit_of_measurement = uom if uom else None

        dc = attr_data.get("device_class")
        if dc:
            self._attr_device_class = dc

        sc = attr_data.get("state_class")
        if sc:
            try:
                self._attr_state_class = SensorStateClass(sc)
            except ValueError:
                _LOGGER.warning("UDS: unknown state_class %r for %s, ignoring", sc, attr_key)

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> dr.DeviceInfo | None:
        if self._device_entry is not None:
            return dr.DeviceInfo(identifiers=self._device_entry.identifiers)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            ATTR_DEVICE_ID: self._device_id,
            ATTR_DEVICE_NAME: self._device_name,
            ATTR_ATTRIBUTE_NAME: self._attr_data.get("name", self._attr_key),
            ATTR_ATTRIBUTE_KEY: self._attr_key,
            ATTR_ATTRIBUTE_VALUE: self._attr_data.get("value"),
            ATTR_MANAGED: True,
        }

        notes = self._attr_data.get("notes")
        if notes:
            attrs["uds_notes"] = notes

        if self._device_entry:
            dev = self._device_entry
            attrs[ATTR_DEVICE_MANUFACTURER] = _dev_attr(dev, "manufacturer")
            attrs[ATTR_DEVICE_MODEL] = _dev_attr(dev, "model")
            attrs[ATTR_DEVICE_MODEL_ID] = _dev_attr(dev, "model_id")
            attrs[ATTR_DEVICE_SERIAL] = _dev_attr(dev, "serial_number")
            attrs[ATTR_DEVICE_SW_VERSION] = _dev_attr(dev, "sw_version")
            attrs[ATTR_DEVICE_HW_VERSION] = _dev_attr(dev, "hw_version")
            attrs[ATTR_DEVICE_CONFIG_URL] = _dev_attr(dev, "configuration_url")

        return attrs

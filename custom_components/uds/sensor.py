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
    ATTR_ATTRIBUTE_KEY,
    ATTR_ATTRIBUTE_NAME,
    ATTR_ATTRIBUTE_VALUE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_MANAGED,
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
    # Data is stored in entry.data["devices"]; fall back to entry.options for
    # entries created by older versions of this integration.
    devices_data: dict[str, Any] = (
        config_entry.data.get("devices")
        or config_entry.options.get("devices")
        or {}
    )

    _LOGGER.debug("UDS setup: found %d device(s) in storage", len(devices_data))

    dev_reg = dr.async_get(hass)
    entities: list[UDSSensor] = []

    for device_id, device_data in devices_data.items():
        device_name = device_data.get("device_name", device_id)
        device_entry = dev_reg.async_get(device_id)
        identifiers = device_entry.identifiers if device_entry else None

        for attr_key, attr_data in device_data.get("attributes", {}).items():
            _LOGGER.debug(
                "UDS: creating sensor for device=%s attr=%s value=%r",
                device_name,
                attr_key,
                attr_data.get("value"),
            )
            entities.append(
                UDSSensor(
                    device_id=device_id,
                    device_name=device_name,
                    device_identifiers=identifiers,
                    attr_key=attr_key,
                    attr_data=attr_data,
                )
            )

    _LOGGER.debug("UDS setup: adding %d sensor entity/entities", len(entities))
    async_add_entities(entities)


class UDSSensor(SensorEntity):
    """Sensor for a single user-defined device attribute."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        device_id: str,
        device_name: str,
        device_identifiers: set | None,
        attr_key: str,
        attr_data: dict[str, Any],
    ) -> None:
        self._device_id = device_id
        self._device_name = device_name
        self._device_identifiers = device_identifiers
        self._attr_key = attr_key
        self._attr_data = attr_data

        device_slug = _slugify(device_name)
        self._attr_unique_id = f"uds_{device_id}_{attr_key}"
        # Suggest the entity_id slug; HA generates the final entity_id and
        # the entity registry preserves it across reloads.
        self._attr_suggested_object_id = f"uds_{device_slug}_{attr_key}"
        self._attr_name = f"{device_name} {attr_data.get('name', attr_key)}"
        self._attr_native_value = attr_data.get("value") or None

        icon = attr_data.get("icon")
        self._attr_icon = icon or None

        uom = attr_data.get("unit_of_measurement")
        self._attr_native_unit_of_measurement = uom or None

        dc = attr_data.get("device_class")
        if dc:
            self._attr_device_class = dc

        sc = attr_data.get("state_class")
        if sc:
            try:
                self._attr_state_class = SensorStateClass(sc)
            except ValueError:
                _LOGGER.warning("UDS: unknown state_class %r for %s", sc, attr_key)

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> dict | None:
        if self._device_identifiers:
            return {"identifiers": self._device_identifiers}
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_DEVICE_ID: self._device_id,
            ATTR_DEVICE_NAME: self._device_name,
            ATTR_ATTRIBUTE_NAME: self._attr_data.get("name", self._attr_key),
            ATTR_ATTRIBUTE_KEY: self._attr_key,
            ATTR_ATTRIBUTE_VALUE: self._attr_data.get("value"),
            ATTR_MANAGED: True,
        }

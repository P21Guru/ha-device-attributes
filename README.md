# User-Defined Device Sensors (UDS)

A Home Assistant custom integration that lets you attach custom metadata to any existing HA device and expose each attribute as a normal sensor entity — no YAML required.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

## Features

- Select any existing HA device and add custom name/value attributes through the UI
- Each attribute becomes a `sensor.uds_<device>_<attribute>` entity with a live state
- Optional icon, unit of measurement, device class, state class, and notes per attribute
- Sensors appear linked to the original device in its entity list
- Stable unique IDs that survive friendly-name changes
- Full options flow: add new devices, add, edit, and delete attributes without YAML
- Services for automation-driven attribute management
- HACS-compatible

## Installation via HACS

1. In HACS, go to **Integrations → Custom repositories**
2. Add `https://github.com/p21guru/ha-device-attributes` with category **Integration**
3. Install **User-Defined Device Sensors**
4. Restart Home Assistant

## Manual Installation

Copy `custom_components/uds/` into your `<config>/custom_components/` directory and restart.

## Configuration

### Adding attributes

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **User-Defined Device Sensors**
3. Select a device from the dropdown
4. Fill in the attribute form:

| Field | Required | Description |
|-------|----------|-------------|
| Attribute Name | Yes | Human-readable label (e.g. `Filter Model`) |
| Attribute Value | Yes | The value to store (e.g. `LT1000P`) |
| Icon | No | MDI icon (e.g. `mdi:filter`) |
| Unit of Measurement | No | e.g. `°C`, `%`, `km` |
| Device Class | No | HA sensor device class (e.g. `temperature`) |
| State Class | No | `measurement`, `total`, or `total_increasing` |
| Notes | No | Private notes — stored but not exposed as a sensor attribute |

5. Save — a sensor is created immediately

### Managing existing attributes

Open the integration's **Configure** menu to:
- **Edit** an attribute's name, value, or metadata
- **Delete** an attribute (removes the sensor)
- **Add new attributes** to an existing or new device

Multiple devices can be managed within a single integration instance.

## Entity Naming

Suggested entity IDs follow the pattern:
```
sensor.uds_<device_slug>_<attribute_slug>
```

Examples:
```
sensor.uds_refrigerator_filter_model
sensor.uds_refrigerator_reorder_url
sensor.uds_hvac_filter_size
sensor.uds_living_room_purifier_location_note
```

The entity registry preserves your entity IDs across reloads even if the device or attribute name changes.

## Sensor State & Attributes

The sensor **state** is the user-defined value string.

Each sensor exposes these extra attributes:

| Attribute | Description |
|-----------|-------------|
| `uds_device_id` | Linked HA device ID |
| `uds_device_name` | Linked device friendly name |
| `uds_attribute_name` | Human-readable attribute name |
| `uds_attribute_key` | Slugified attribute key |
| `uds_attribute_value` | Current value (mirrors state) |
| `uds_managed` | Always `true` — useful for filtering in templates |

## Services

### `uds.set_attribute_value`
Update an attribute's value. Triggers an immediate sensor state update.
```yaml
service: uds.set_attribute_value
data:
  device_id: abc123def456
  attribute_key: filter_model
  value: LT1000P-2
```

### `uds.create_attribute`
Create a new attribute via automation or script.
```yaml
service: uds.create_attribute
data:
  device_id: abc123def456
  name: Warranty Date
  value: "2027-01-15"
  icon: mdi:calendar          # optional
  unit_of_measurement: ""     # optional
  device_class: ""            # optional
  state_class: ""             # optional
```

### `uds.delete_attribute`
Remove an attribute and its sensor.
```yaml
service: uds.delete_attribute
data:
  device_id: abc123def456
  attribute_key: warranty_date
```

### `uds.reload`
Reload the integration and refresh all sensors.
```yaml
service: uds.reload
```

> **Finding your device ID**: In HA, go to **Settings → Devices & Services**, open the device, then copy the ID from the URL (`/config/devices/device/abc123def456`).

## Dashboard Usage

```yaml
type: entities
title: Refrigerator Details
entities:
  - entity: sensor.uds_refrigerator_filter_model
    name: Filter Model
  - entity: sensor.uds_refrigerator_reorder_url
    name: Reorder URL
  - entity: sensor.uds_refrigerator_warranty_date
    name: Warranty Date
```

Template:
```yaml
{{ states('sensor.uds_refrigerator_filter_model') }}
```

Filter all UDS sensors in a template:
```yaml
{{ states.sensor | selectattr('attributes.uds_managed', 'eq', true) | list }}
```

## Data Storage

All data is stored in Home Assistant's config entry `data` storage (`.storage/core.config_entries`). The integration **never modifies** `core.device_registry` or any other native HA storage.

Storage structure per config entry:
```json
{
  "devices": {
    "<device_id>": {
      "device_name": "Refrigerator",
      "attributes": {
        "filter_model": {
          "name": "Filter Model",
          "value": "LT1000P",
          "icon": "mdi:filter",
          "unit_of_measurement": null,
          "device_class": null,
          "state_class": null,
          "notes": null
        }
      }
    }
  }
}
```

## Requirements

- Home Assistant 2023.1.0 or newer
- HACS (for HACS installation)

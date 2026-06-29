# User-Defined Device Sensors (UDS)

A Home Assistant custom integration that lets you attach custom metadata attributes to any existing Home Assistant device and expose each attribute as a normal sensor entity.

## Features

- Select any existing HA device and add custom name/value attributes through the UI
- Each attribute becomes a `sensor.uds_<device>_<attribute>` entity
- Stable unique IDs that survive friendly-name changes
- Sensors are associated with the original HA device (appear in its entity list)
- Read-only native device metadata (manufacturer, model, serial, etc.) surfaced as sensor attributes
- Full options flow: add, edit, and delete attributes without YAML
- Services for automation-driven attribute management
- HACS-compatible structure

## Installation via HACS

1. In HACS, go to **Integrations → Custom repositories**
2. Add `https://github.com/p21guru/ha-device-attributes` with category **Integration**
3. Install **User-Defined Device Sensors**
4. Restart Home Assistant

## Manual Installation

Copy `custom_components/uds/` into your `<config>/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **User-Defined Device Sensors**
3. Select a device
4. Enter an attribute name and value (e.g. `Filter Model` / `LT1000P`)
5. Save — a sensor is created immediately

## Entity Naming

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

## Sensor State & Attributes

The sensor **state** is the user-defined value.

Each sensor exposes these attributes:

| Attribute | Description |
|-----------|-------------|
| `uds_device_id` | Linked HA device ID |
| `uds_device_name` | Linked device friendly name |
| `uds_attribute_name` | Human-readable attribute name |
| `uds_attribute_key` | Slugified attribute key |
| `uds_attribute_value` | Current value (mirrors state) |
| `uds_managed` | Always `true` |
| `device_manufacturer` | Read-only from device registry |
| `device_model` | Read-only from device registry |
| `device_model_id` | Read-only from device registry |
| `device_serial_number` | Read-only from device registry |
| `device_sw_version` | Read-only from device registry |
| `device_hw_version` | Read-only from device registry |
| `device_configuration_url` | Read-only from device registry |

## Services

### `uds.set_attribute_value`
Update an attribute value (triggers sensor state update).
```yaml
service: uds.set_attribute_value
data:
  device_id: abc123
  attribute_key: filter_model
  value: LT1000P-2
```

### `uds.create_attribute`
Create a new attribute via automation or script.
```yaml
service: uds.create_attribute
data:
  device_id: abc123
  name: Warranty Date
  value: "2027-01-15"
  icon: mdi:calendar
```

### `uds.delete_attribute`
Remove an attribute and its sensor.
```yaml
service: uds.delete_attribute
data:
  device_id: abc123
  attribute_key: warranty_date
```

### `uds.reload`
Reload the integration and refresh all sensors.
```yaml
service: uds.reload
```

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

Template usage:
```yaml
{{ states('sensor.uds_refrigerator_filter_model') }}
```

## Data Storage

All data is stored in Home Assistant's config entry options storage. The integration **never modifies** `core.device_registry` or any other native HA storage.

Storage structure:
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
          "state_class": null
        }
      }
    }
  }
}
```

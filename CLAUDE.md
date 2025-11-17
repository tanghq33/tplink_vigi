# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for TP-Link VIGI security cameras. The integration receives webhook notifications from VIGI cameras for events like motion detection, person detection, vehicle detection, and line crossing. It provides binary sensor entities grouped under device entities for each camera.

**Configuration:** UI-based only (no YAML support)

## Architecture

### Integration Structure

The codebase follows Home Assistant's modern config entry structure:

- **`custom_components/tplink_vigi/`**: Main integration directory
  - **`__init__.py`**: Integration entry point, handles config entries and platform setup
  - **`config_flow.py`**: UI configuration flow for adding/managing cameras
  - **`manifest.json`**: Integration metadata and dependencies
  - **`const.py`**: Shared constants including domain name and event types
  - **`binary_sensor.py`**: Binary sensor platform for motion detection (on/off)
  - **`strings.json`**: UI text and error messages
  - **`translations/en.json`**: English translations

### Config Entry Pattern

The integration uses Home Assistant's config entry system (UI configuration):

1. Users add cameras through the Home Assistant UI (Settings → Integrations → Add Integration → TP-Link VIGI)
2. Each camera is configured with:
   - **Name** (required): Display name for the camera
   - **Webhook ID** (optional): Custom webhook identifier, auto-generated from name if not provided
3. The integration creates a Device entity for each camera
4. Binary sensor entities are created under each camera device
5. Webhooks are registered at `/api/webhook/{webhook_id}`
6. Camera state is stored in `hass.data[DOMAIN][entry_id]["cameras"][camera_id]`

### Webhook Pattern

The webhook-based architecture:

1. Each camera gets a webhook registered at `/api/webhook/{webhook_id}`
2. Webhook ID is either:
   - **Custom**: User-specified during setup (e.g., "front_door")
   - **Auto-generated**: Derived from camera name via `name.lower().replace(" ", "_")` (e.g., "Front Door Camera" → "front_door_camera")
3. TP-Link VIGI cameras POST event data to these webhooks
4. The webhook handlers parse the event data and update entity states
5. Binary sensors auto-reset to OFF after 5 seconds (configurable via RESET_DELAY constant)

### Entity Types

**Binary Sensor (binary_sensor.py)**:
- Entity name format: `{camera_name} Motion`
- Device class: MOTION
- State: Boolean (on when event detected, auto-resets to off after 5 seconds)
- Attributes: device_name, ip, mac, event_type (list), event_type_string, event_time, last_triggered
- `RESET_DELAY = 5` controls auto-reset timing
- Grouped under Device entity for the camera
- Unique ID: `{entry_id}_{camera_id}_motion`

**Device (Device Registry)**:
- Device name: Camera name (e.g., "Front Door Camera")
- Manufacturer: TP-Link
- Model: VIGI Camera
- Identifiers: `(DOMAIN, camera_id)`
- Contains binary sensor entities for the camera

### Webhook Payload Format

Both platforms expect webhook data in this structure:
```json
{
  "device_name": "Camera Name",
  "ip": "192.168.1.100",
  "mac": "AA:BB:CC:DD:EE:FF",
  "event_list": [
    {
      "dateTime": "20250117120000",  // Format: YYYYMMDDHHmmss
      "event_type": ["motion", "person"]  // List of event types
    }
  ]
}
```

## Configuration

The integration uses UI-based configuration through Home Assistant's config flow system:

### Adding the Integration

1. Navigate to **Settings** → **Devices & Services** → **Integrations**
2. Click **Add Integration** and search for "TP-Link VIGI"
3. Enter camera name (required) and optionally a custom webhook ID
4. The webhook URL will be displayed (e.g., `http://your-ha:8123/api/webhook/front_door_camera`)
5. Configure your VIGI camera to POST events to this webhook URL
6. Optionally add more cameras during initial setup

### Managing Cameras (Options Flow)

After initial setup, you can manage cameras via the integration's configure menu:

- **Add Camera**: Add a new camera to the integration
- **Edit Camera**: Modify camera name or webhook ID (warning: changing webhook ID requires camera reconfiguration)
- **Remove Camera**: Remove a camera and unregister its webhook

### Config Entry Data Structure

```python
{
  "cameras": [
    {
      "name": "Front Door Camera",
      "webhook_id": "front_door_camera"  # Auto-generated or custom
    },
    {
      "name": "Backyard Camera",
      "webhook_id": "backyard_cam"  # Custom webhook ID
    }
  ]
}
```

## Development Notes

### Testing Webhooks

To test webhook functionality manually:
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/front_door_camera \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Front Door Camera",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "event_list": [{
      "dateTime": "20250117120000",
      "event_type": ["motion", "person"]
    }]
  }'
```

### Key Implementation Details

- **Webhook ID**: Either custom (user-specified) or auto-generated via `camera_name.lower().replace(" ", "_")`
- **DateTime parsing**: Events use custom format `YYYYMMDDHHmmss`, parsed via `datetime.strptime(date_time_str, "%Y%m%d%H%M%S")` (binary_sensor.py:181)
- **Async reset mechanism**: Binary sensors use `asyncio.create_task()` for auto-reset, canceling previous tasks if new events arrive (binary_sensor.py:227)
- **Data storage**: Camera state stored in `hass.data[DOMAIN][entry_id]["cameras"][camera_id]`
- **Unique ID format**: `{entry_id}_{camera_id}_motion` for entities
- **Device identifiers**: `(DOMAIN, camera_id)` for device registry
- **Webhook cleanup**: Webhooks automatically unregistered when integration is unloaded or cameras are removed
- **Config entry setup**: Uses `async_setup_entry()` in both `__init__.py` and `binary_sensor.py`
- **Options flow**: Supports adding, editing, and removing cameras post-setup with automatic reload

### Event Types

Defined in const.py but not currently enforced:
- `EVENT_MOTION = "motion"`
- `EVENT_PERSON = "person"`
- `EVENT_VEHICLE = "vehicle"`
- `EVENT_LINE_CROSSING = "line_crossing"`

Actual event types come from webhook payload's `event_type` field.

## Python Environment

- Requires Python 3.13+ (based on `__pycache__` files)
- Uses Home Assistant core libraries (no additional requirements specified)
- Type hints using `from __future__ import annotations` for forward compatibility

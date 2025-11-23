# Data Model: TPLink Vigi Webhook Motion Detection

**Feature**: 001-webhook-motion-events
**Date**: 2025-11-20
**Input**: Feature specification and research findings

## Overview

This document defines the data structures for the TPLink Vigi webhook motion detection integration. The model supports webhook-based event notification with optional image capture, storing only the most recent event and image per camera.

## Entities

### Camera Device

Represents a physical TPLink Vigi camera in Home Assistant.

**Attributes:**
- `identifiers`: Set of (domain, camera_id) tuples for device identification
- `name`: User-friendly camera name (e.g., "Front Door Camera")
- `manufacturer`: "TP-Link"
- `model`: "VIGI Camera"

**Relationships:**
- Parent device for Motion Binary Sensor entity
- Parent device for Motion Image entity

**Lifecycle:**
- Created during config entry setup
- Persists across Home Assistant restarts
- Removed when integration instance deleted

---

### Motion Binary Sensor Entity

Binary sensor indicating current motion detection state.

**Base Class**: `homeassistant.components.binary_sensor.BinarySensorEntity`

**Core Attributes:**
- `unique_id`: `{entry_id}_{camera_id}_motion` (stable across restarts)
- `name`: `{camera_name} Motion`
- `device_class`: `BinarySensorDeviceClass.MOTION`
- `is_on`: `bool` - True when motion detected, False when clear
- `device_info`: Links to Camera Device

**State Attributes:**
```python
{
    "device_name": str,        # Camera's self-reported name
    "ip": str,                  # Camera IP address
    "mac": str,                 # Camera MAC address
    "event_type": list[str],    # List of event types (e.g., ["motion", "person"])
    "event_type_string": str,   # Comma-separated event types
    "event_time": str | None,   # ISO format timestamp of event
    "last_triggered": str,      # ISO format timestamp when HA received event
}
```

**State Transitions:**
1. `off` (clear) → `on` (detected): When webhook receives motion event
2. `on` (detected) → `off` (clear): After reset_delay seconds with no new events

**Validation Rules:**
- `is_on` must be boolean (never None after initialization)
- `event_time` parsed from camera datetime string (format: YYYYMMDDHHmmss)
- `last_triggered` always set when state changes to `on`

**Data Retention:**
- Only most recent event retained
- Previous events overwritten by new events
- State cleared on Home Assistant restart (acceptable per spec edge case 7)

---

### Motion Image Entity

Stores and displays the most recent captured motion image.

**Base Class**: `homeassistant.components.image.ImageEntity`

**Core Attributes:**
- `unique_id`: `{entry_id}_{camera_id}_last_image` (stable across restarts)
- `name`: `{camera_name} Last Image`
- `content_type`: Dynamic based on image format (default "image/jpeg")
- `device_info`: Links to Camera Device

**State Attributes:**
```python
{
    "image_last_updated": str,  # ISO format timestamp when image captured
    "image_size": int,           # Size in bytes
    "image_width": int | None,   # Image width in pixels (if parseable)
    "image_height": int | None,  # Image height in pixels (if parseable)
}
```

**Image Data:**
- Stored as `bytes` in memory (`_image_bytes` attribute)
- Served via `async_image()` method to Home Assistant frontend
- Maximum recommended size: 5MB (warning logged if exceeded per FR-023)

**Data Retention:**
- Only most recent image retained
- Previous images overwritten by new images
- Image persists across Home Assistant restarts (stored in entity state)

**Validation Rules:**
- Image bytes validated for size (warn if > 5MB)
- Content-Type detected from multipart part or defaulted to "image/jpeg"
- Image must be valid binary data (not validated for format correctness)

---

## Configuration Entry Schema

Home Assistant config entry data structure.

```python
{
    "cameras": [
        {
            "camera_id": str,      # Permanent UUID (uuid.uuid4())
            "name": str,            # User-provided camera name
            "webhook_id": str,      # Auto-generated UUID (uuid.uuid4())
            "reset_delay": int,     # Seconds to wait before clearing motion state (1-60)
        }
    ]
}
```

**Field Definitions:**

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `camera_id` | str (UUID) | Yes | Generated | UUID format | Permanent device identifier, never changes |
| `name` | str | Yes | None | Non-empty | User-friendly camera name |
| `webhook_id` | str (UUID) | Yes | Generated | UUID format | Webhook endpoint identifier, non-editable after creation |
| `reset_delay` | int | No | 5 | 1 ≤ value ≤ 60 | Seconds to wait before auto-reset to clear state |

**Constraints:**
- `camera_id` must be unique across all integration instances
- `webhook_id` must be unique across all integration instances
- `name` can be duplicated (user responsibility to distinguish)
- `reset_delay` validated on input, defaults applied if missing

**Migration Notes:**
- Existing configs with user-provided `webhook_id` remain valid (backward compatible)
- If `camera_id` missing, generated on first load and persisted

---

## Runtime State Schema

Runtime state stored in `hass.data[DOMAIN][entry_id]`.

```python
{
    "entry": ConfigEntry,      # Reference to config entry
    "cameras": {
        "{camera_id}": {
            "name": str,                        # Camera name (from config)
            "webhook_id": str,                  # Webhook ID (from config)
            "reset_delay": int,                 # Auto-reset delay (from config)
            "is_on": bool,                      # Current motion state
            "last_event": list[str] | None,     # Most recent event types
            "last_event_time": datetime | None, # Timestamp of most recent event
            "last_image": bytes | None,         # Most recent image bytes
            "last_image_time": datetime | None, # Timestamp of most recent image
            "last_image_size": int | None,      # Size of most recent image in bytes
        }
    }
}
```

**Field Definitions:**

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `name` | str | No | Camera name from config |
| `webhook_id` | str | No | Webhook ID from config |
| `reset_delay` | int | No | Auto-reset delay from config |
| `is_on` | bool | No | Current motion detection state |
| `last_event` | list[str] | Yes | Event types from most recent webhook (e.g., ["motion", "person"]) |
| `last_event_time` | datetime | Yes | Python datetime of most recent event |
| `last_image` | bytes | Yes | Raw image bytes from most recent event |
| `last_image_time` | datetime | Yes | Python datetime when most recent image captured |
| `last_image_size` | int | Yes | Size of most recent image in bytes |

**Lifecycle:**
- Initialized when config entry loaded (`async_setup_entry`)
- Updated by webhook handler when events received
- Updated by binary sensor entity during state changes
- Updated by image entity when images received
- Cleaned up when config entry unloaded (`async_unload_entry`)

**Concurrency:**
- Access synchronized via Home Assistant event loop (single-threaded)
- No explicit locking required
- Webhook handler updates are atomic (per camera_id)

---

## Webhook Payload Schemas

### JSON Format (Motion Event Without Image)

**Content-Type**: `application/json`

**Schema**:
```json
{
    "device_name": "string",     // Camera's self-reported name
    "ip": "string",               // Camera IP address (e.g., "192.168.1.100")
    "mac": "string",              // Camera MAC address (e.g., "AA:BB:CC:DD:EE:FF")
    "event_list": [               // List of events (typically one)
        {
            "dateTime": "string", // Format: YYYYMMDDHHmmss (e.g., "20231120150530")
            "event_type": ["string"]  // Array of event types (e.g., ["motion"])
        }
    ]
}
```

**Field Constraints:**
- `device_name`: Optional, defaults to "Unknown"
- `ip`: Optional, defaults to "Unknown"
- `mac`: Optional, defaults to "Unknown"
- `event_list`: Required, must be non-empty array
- `event_list[0].dateTime`: Optional, used for event timestamp
- `event_list[0].event_type`: Optional, defaults to ["unknown"]

**Example:**
```json
{
    "device_name": "Front Door Camera",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "event_list": [
        {
            "dateTime": "20231120150530",
            "event_type": ["motion"]
        }
    ]
}
```

---

### Multipart Form (Motion Event With Image)

**Content-Type**: `multipart/form-data; boundary={boundary}`

**Parts:**

1. **event part** (JSON metadata):
   ```
   Content-Disposition: form-data; name="event"
   Content-Type: application/json

   {same schema as JSON format above, sent as bytearray}
   ```

2. **image part** (binary image):
   ```
   Content-Disposition: form-data; name="20251123180936"
   Content-Type: image/jpeg

   <binary image data as bytearray>
   ```

**Field Constraints:**
- `event` part: Required, contains event metadata as bytearray (needs UTF-8 decoding)
- Image part: Optional, field name is variable (uses event datetime string)
- Image Content-Type: Typically "image/jpeg"
- Image filename: Not included by camera
- Image format: JPEG starting with `\xff\xd8\xff\xdb` signature

**Parsing Logic:**
```python
async for part in multipart_reader:
    part_name = part.name

    if part_name == "event":
        # Parse JSON event data
        part_bytes = await part.read()
        event_data = json.loads(part_bytes.decode('utf-8'))
    else:
        # Any other field is treated as image data
        image_bytes = await part.read()
        content_type = part.headers.get("Content-Type", "image/jpeg")
```

**Error Handling:**
- Missing `event` part → log warning, cannot process event (FR-022)
- Missing image part → process event without image (acceptable)
- Malformed JSON in `event` → log warning, cannot process event (FR-022)
- Network interruption during image read → log warning, process event without image (FR-021)

---

## State Machine

### Binary Sensor State Transitions

```
                    ┌─────────────┐
                    │   initial   │
                    │  (is_on =   │
                    │    False)   │
                    └──────┬──────┘
                           │
                           │ webhook event received
                           ▼
                    ┌─────────────┐
             ┌─────►│   motion    │
             │      │  (is_on =   │
             │      │    True)    │
             │      └──────┬──────┘
             │             │
             │             │ reset_delay seconds
new event    │             │ (no new events)
received     │             ▼
             │      ┌─────────────┐
             └──────│   clear     │
                    │  (is_on =   │
                    │    False)   │
                    └─────────────┘
```

**Transition Rules:**
1. New webhook event always sets state to `motion` (even if already in `motion`)
2. New webhook event cancels any pending auto-reset timer
3. Auto-reset timer starts after each state transition to `motion`
4. Home Assistant restart clears state to `clear` (per spec edge case 7)

---

## Data Flow

### Webhook Event Processing

```
Camera                Webhook Handler        Binary Sensor      Image Entity
  │                         │                      │                │
  │  POST /webhook/{uuid}   │                      │                │
  ├────────────────────────►│                      │                │
  │                         │                      │                │
  │                         │ Parse payload        │                │
  │                         │ (JSON or multipart)  │                │
  │                         │                      │                │
  │                         │ Update runtime state │                │
  │                         │ (hass.data)          │                │
  │                         │                      │                │
  │                         │  Update state        │                │
  │                         ├─────────────────────►│                │
  │                         │                      │                │
  │                         │  async_write_ha_state()               │
  │                         │                      │                │
  │                         │  Update image        │                │
  │                         │  (if present)        │                │
  │                         ├──────────────────────┼───────────────►│
  │                         │                      │                │
  │                         │                      │  async_write_ha_state()
  │                         │                      │                │
  │      200 OK             │                      │                │
  │◄────────────────────────┤                      │                │
  │                         │                      │                │
  │                         │  Schedule auto-reset │                │
  │                         │  task (reset_delay)  │                │
  │                         ├─────────────────────►│                │
  │                         │                      │                │
  │                         │  ... wait ...        │                │
  │                         │                      │                │
  │                         │  Reset to clear      │                │
  │                         │  async_write_ha_state()               │
  │                         │                      │                │
```

---

## Database Schema

**Not Applicable**: This integration does not use a database. All state is stored in:
1. Home Assistant config entries (persistent configuration)
2. Home Assistant entity states (persisted by HA core)
3. Runtime memory (`hass.data`) for transient state
4. Image bytes in memory (non-persistent, cleared on restart is acceptable)

---

## Summary

- **2 entity types**: Binary Sensor (motion detection), Image (last captured image)
- **1 device type**: Camera Device (parent for entities)
- **Config storage**: Home Assistant config entries (JSON)
- **Runtime storage**: `hass.data` dictionary (in-memory)
- **Image storage**: Entity state (bytes in memory)
- **State persistence**: Home Assistant entity state mechanism
- **Data retention**: Only most recent event and image per camera
- **Concurrency**: Single-threaded via HA event loop, no explicit locking needed

All data structures align with Home Assistant conventions and specification requirements (FR-001 through FR-027).

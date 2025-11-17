# UI Configuration Migration - Context and Reference

**Last Updated: 2025-01-17**

---

## Quick Reference

### Key Files and Their Roles

| File | Current State | Required Changes | Priority |
|------|---------------|------------------|----------|
| `__init__.py` | YAML-only setup | Add config entry support | HIGH |
| `binary_sensor.py` | Platform setup | Migrate to entry setup + devices | HIGH |
| `const.py` | Basic constants | Add config flow constants | MEDIUM |
| `manifest.json` | Has config_flow:true | No changes needed | LOW |
| `config_flow.py` | **MISSING** | Create from scratch | HIGH |
| `strings.json` | **MISSING** | Create from scratch | HIGH |
| `translations/en.json` | **MISSING** | Create from scratch | MEDIUM |

---

## Current Architecture Deep Dive

### Data Flow Diagram
```
┌─────────────────┐
│  configuration  │
│     .yaml       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   async_setup   │  (__init__.py)
│  Initialize     │
│  hass.data      │
└─────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  async_setup_platform           │  (binary_sensor.py)
│  - Parse YAML                   │
│  - Generate camera_ids          │
│  - Register webhooks            │
│  - Create entities              │
└────────┬────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Webhook: /api/webhook/{id}      │
│  ├─ Receive POST from camera     │
│  ├─ Parse event data             │
│  ├─ Update entity state          │
│  └─ Schedule auto-reset (5s)     │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Binary Sensor Entity            │
│  ├─ State: on/off                │
│  ├─ Device class: motion         │
│  └─ Attributes: event details    │
└──────────────────────────────────┘
```

---

## Target Architecture

### New Data Flow Diagram
```
┌─────────────────┐
│   Home Assistant│
│   UI Integration│
│   Add Dialog    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  ConfigFlow                     │
│  - User inputs camera name      │
│  - Optional webhook_id          │
│  - Validate uniqueness          │
│  - Display webhook URL          │
│  - Create config entry          │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  async_setup_entry (__init__.py)│
│  - Initialize entry data        │
│  - Forward to platforms         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  async_setup_entry (binary)     │
│  - Read cameras from entry      │
│  - Create Device entities       │
│  - Register webhooks            │
│  - Create binary sensors        │
└────────┬────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Device Registry                 │
│  ├─ Device per camera            │
│  ├─ Manufacturer: TP-Link        │
│  ├─ Model: VIGI Camera           │
│  └─ Binary sensor under device   │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  OptionsFlow                     │
│  ├─ Add camera                   │
│  ├─ Edit camera                  │
│  └─ Remove camera                │
└──────────────────────────────────┘
```

---

## Critical Implementation Details

### 1. Camera ID vs Webhook ID

**Current Behavior:**
```python
camera_id = camera_name.lower().replace(" ", "_")
# "Front Door Camera" → "front_door_camera"
```

**New Behavior:**
- **camera_id**: Still derived from name for backward compat (internal use)
- **webhook_id**: User-customizable OR auto-generated
- Users can set webhook_id = "front_door" even if name is "Front Door Camera"

**Impact:**
- Webhook URL can differ from auto-generated format
- Must store webhook_id separately in config entry
- Must validate webhook_id uniqueness across ALL entries

---

### 2. Data Storage Restructuring

**Current:**
```python
hass.data[DOMAIN][camera_id] = {
    "name": str,
    "is_on": bool,
    "last_event": list,
    "last_event_time": datetime
}
```

**New:**
```python
hass.data[DOMAIN][entry_id] = {
    "entry": ConfigEntry,
    "cameras": {
        camera_id: {
            "name": str,
            "webhook_id": str,
            "is_on": bool,
            "last_event": list,
            "last_event_time": datetime
        }
    }
}
```

**Why:**
- Namespace by entry_id to support multiple integration instances
- Store webhook_id for proper cleanup
- Keep entry reference for reload/update operations

---

### 3. Webhook Registration Timing

**Critical:** Webhooks MUST be registered in platform setup, NOT in __init__.py

**Reason:** Webhook handler needs entity instance reference to call entity methods

**Current (Correct):**
```python
# In binary_sensor.py async_setup_platform()
sensor = VigiCameraBinarySensor(...)
webhook_register(hass, DOMAIN, name, webhook_id, sensor.handle_webhook)
```

**Must Maintain:**
```python
# In binary_sensor.py async_setup_entry()
sensor = VigiCameraBinarySensor(...)
webhook_register(hass, DOMAIN, name, webhook_id, sensor.handle_webhook)
```

---

### 4. Unique ID Strategy

**Current:**
```python
self._attr_unique_id = f"tplink_vigi_{camera_id}"
# "tplink_vigi_front_door_camera"
```

**New (Recommended):**
```python
self._attr_unique_id = f"{entry.entry_id}_{camera_id}_motion"
# "01234567890abcdef_front_door_camera_motion"
```

**Why:**
- Allows multiple integration instances
- Prevents collisions if same camera name used in different entries
- "_motion" suffix allows future sensor types (e.g., "_event")

---

### 5. Device Info Structure

**Implementation:**
```python
from homeassistant.helpers.entity import DeviceInfo

@property
def device_info(self) -> DeviceInfo:
    """Return device information."""
    return DeviceInfo(
        identifiers={(DOMAIN, self._camera_id)},
        name=self._camera_name,
        manufacturer="TP-Link",
        model="VIGI Camera",
        sw_version=self._attributes.get("firmware", "Unknown"),
        configuration_url=None,  # Could add camera web UI if available
    )
```

**Benefits:**
- Cameras appear as devices in HA UI
- Binary sensor grouped under camera device
- Can add multiple entities to same device later (e.g., regular sensor)

---

## Key Decisions Made

### Decision 1: UI-Only, No YAML Support
**Rationale:**
- Simplifies codebase
- Follows modern HA integration patterns
- Most users prefer UI configuration
- YAML support adds complexity without significant benefit

**Impact:**
- Existing YAML configs will stop working after upgrade
- Need clear documentation for migration
- Could add YAML import flow in future if needed

---

### Decision 2: Custom Webhook IDs Allowed
**Rationale:**
- User requested ability to customize webhook URLs
- Allows shorter, cleaner URLs
- Supports organizing cameras by location/purpose

**Impact:**
- Must validate webhook_id format and uniqueness
- Must handle webhook_id changes (requires unregister + re-register)
- Must display webhook URL clearly during setup

**Validation Rules:**
- Only lowercase letters, numbers, underscores
- Must be unique across all cameras in all entries
- Cannot be empty
- Regex: `^[a-z0-9_]+$`

---

### Decision 3: Device Registry Integration
**Rationale:**
- Follows HA best practices
- Better UI organization
- Enables future expansion (more entity types)
- Professional appearance

**Impact:**
- More code complexity
- Must implement DeviceInfo properly
- Device lifecycle tied to entity lifecycle

---

### Decision 4: No Configuration for Reset Delay
**Rationale:**
- Keeping it simple (user requested)
- 5 seconds is reasonable default
- Can be added later if users request
- Avoids UI clutter

**Impact:**
- Reset delay remains hardcoded at 5 seconds
- Easy to add later as optional parameter

---

## Webhook Payload Reference

### Expected Format (from VIGI cameras)
```json
{
  "device_name": "Front Door Camera",
  "ip": "192.168.1.100",
  "mac": "AA:BB:CC:DD:EE:FF",
  "event_list": [
    {
      "dateTime": "20250117120000",
      "event_type": ["motion", "person"]
    }
  ]
}
```

### Field Details
- **device_name**: Camera's configured name (may differ from HA name)
- **ip**: Camera's IP address
- **mac**: Camera's MAC address
- **event_list**: Array of events (usually only one)
  - **dateTime**: Format `YYYYMMDDHHmmss` (no separators!)
  - **event_type**: Array of event types (motion, person, vehicle, line_crossing)

### Current Processing
```python
# Parse datetime
event_time = datetime.strptime(date_time_str, "%Y%m%d%H%M%S")
event_time = dt_util.as_local(event_time)

# Join event types
event_type_str = ", ".join(event_types)  # "motion, person"
```

---

## Entity Attribute Reference

### Current Binary Sensor Attributes
```python
{
    "device_name": "Front Door Camera",      # From webhook
    "ip": "192.168.1.100",                   # From webhook
    "mac": "AA:BB:CC:DD:EE:FF",              # From webhook
    "event_type": ["motion", "person"],      # From webhook (list)
    "event_type_string": "motion, person",   # Formatted for display
    "event_time": "2025-01-17T12:00:00+...", # Parsed and localized
    "last_triggered": "2025-01-17T12:00:00+..." # When webhook received
}
```

### Must Maintain All Attributes
These are user-facing and may be used in automations. Do not remove or rename.

---

## Import Statements Reference

### Current Imports (binary_sensor.py)
```python
from __future__ import annotations
import asyncio
from datetime import datetime
import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.webhook import async_register as webhook_register
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import CONF_CAMERAS, DOMAIN
```

### Additional Imports Needed
```python
# For config entry support
from homeassistant.config_entries import ConfigEntry

# For device registry
from homeassistant.helpers.entity import DeviceInfo

# For webhook unregistration
from homeassistant.components.webhook import async_unregister as webhook_unregister
```

### Config Flow Imports (new file)
```python
from __future__ import annotations
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_WEBHOOK_ID
```

---

## Testing Checklist

### Unit Testing (Manual, No Pytest Yet)

#### Config Flow Tests
- [ ] Add first camera with auto-generated webhook ID
- [ ] Add first camera with custom webhook ID
- [ ] Add multiple cameras in single flow
- [ ] Try duplicate camera name (should fail)
- [ ] Try duplicate webhook ID (should fail)
- [ ] Try invalid webhook ID characters (should fail)
- [ ] Cancel during setup (should not create entry)

#### Options Flow Tests
- [ ] Add camera via options
- [ ] Edit camera name only
- [ ] Edit webhook ID only
- [ ] Edit both name and webhook ID
- [ ] Remove camera
- [ ] Remove all cameras then re-add
- [ ] Cancel during edit (should not apply changes)

#### Webhook Tests
- [ ] Send valid webhook to camera
- [ ] Verify binary sensor turns on
- [ ] Verify attributes populated
- [ ] Wait 5 seconds, verify auto-reset to off
- [ ] Send multiple events rapidly
- [ ] Send malformed JSON (should log error, not crash)
- [ ] Send missing required fields
- [ ] Send invalid datetime format

#### Device Tests
- [ ] Verify device appears in device registry
- [ ] Verify manufacturer/model correct
- [ ] Verify entity grouped under device
- [ ] Rename device, verify entity follows
- [ ] Delete device, verify entity removed

#### Cleanup Tests
- [ ] Remove camera, verify webhook unregistered
- [ ] Remove camera, verify entity removed
- [ ] Remove camera, verify device removed (if last entity)
- [ ] Reload integration, verify webhooks still work
- [ ] Remove integration, verify all cleanup happens
- [ ] Check hass.data for leaks

---

## Common Pitfalls and Solutions

### Pitfall 1: Webhook Not Unregistering
**Symptom:** Webhook returns 200 but entity doesn't exist

**Cause:** Webhook not unregistered when entity removed

**Solution:**
```python
async def async_will_remove_from_hass(self) -> None:
    """Unregister webhook when entity removed."""
    webhook_unregister(self._hass, self._webhook_id)
```

---

### Pitfall 2: State Loss on Reload
**Symptom:** Binary sensor resets to off after integration reload

**Cause:** Runtime state not preserved in hass.data

**Solution:** Runtime state (is_on, last_event) is intentionally volatile. This is correct behavior - binary sensor should start in off state.

---

### Pitfall 3: Duplicate Unique IDs
**Symptom:** Entity doesn't appear or multiple entities conflict

**Cause:** Unique ID collision when multiple entries exist

**Solution:** Include entry_id in unique_id:
```python
self._attr_unique_id = f"{entry.entry_id}_{camera_id}_motion"
```

---

### Pitfall 4: Options Not Applying
**Symptom:** Changes in options flow don't take effect

**Cause:** Config entry not updated or reload not triggered

**Solution:**
```python
# In options flow
self.hass.config_entries.async_update_entry(
    self.config_entry,
    data=new_data
)
await self.hass.config_entries.async_reload(self.config_entry.entry_id)
```

---

### Pitfall 5: Device Not Showing Entities
**Symptom:** Device exists but entity not grouped under it

**Cause:** device_info property not implemented or identifiers don't match

**Solution:** Ensure device_info uses same identifiers:
```python
# When creating device
DeviceInfo(identifiers={(DOMAIN, camera_id)})

# When creating entity
@property
def device_info(self):
    return DeviceInfo(identifiers={(DOMAIN, self._camera_id)})
```

---

## File-by-File Implementation Guide

### File: `config_flow.py` (NEW)
**Lines of Code:** ~200-250

**Key Classes:**
- `VigiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN)`
- `VigiOptionsFlow(config_entries.OptionsFlow)`

**Key Methods:**
- `async_step_user()` - Initial setup
- `async_step_add_camera()` - Add camera form
- `async_step_confirm()` - Show webhook URL
- `_generate_webhook_id()` - Helper for ID generation
- `_validate_webhook_id()` - Validation helper
- `async_get_options_flow()` - Create options flow
- OptionsFlow: `async_step_init()`, `async_step_add_camera()`, `async_step_edit_camera()`, `async_step_remove_camera()`

---

### File: `__init__.py` (MODIFY)
**Current:** 15 lines
**Target:** ~80-100 lines

**Add:**
- `async_setup_entry(hass, entry)` - Config entry setup
- `async_unload_entry(hass, entry)` - Cleanup on removal
- `async_update_options(hass, entry)` - Options change handler

**Remove/Deprecate:**
- `async_setup()` - YAML support (keep stub that returns True)

---

### File: `binary_sensor.py` (MAJOR MODIFICATION)
**Current:** 190 lines
**Target:** ~220-250 lines

**Replace:**
- `async_setup_platform()` → `async_setup_entry()`
- Remove PLATFORM_SCHEMA and voluptuous validation

**Add:**
- `device_info` property to entity class
- `async_will_remove_from_hass()` method
- Entry parameter to entity __init__
- Webhook unregistration logic

**Modify:**
- Constructor signature
- Unique ID format
- Data storage namespace (entry_id)

---

### File: `const.py` (EXPAND)
**Current:** 11 lines
**Target:** ~40-50 lines

**Add:**
- CONF_WEBHOOK_ID
- CONF_ENABLED
- Config flow step IDs
- Error message keys
- Validation constants

---

### File: `strings.json` (NEW)
**Lines:** ~100-120 (JSON)

**Sections:**
- config.step.user
- config.step.confirm
- config.error
- config.abort
- options.step.init
- options.step.add_camera
- options.step.edit_camera
- options.step.remove_camera

---

### File: `translations/en.json` (NEW)
**Lines:** Same as strings.json (copy)

---

### File: `manifest.json` (NO CHANGES)
Already has `"config_flow": true`

---

## Reference: Home Assistant APIs

### ConfigFlow Methods
```python
async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
    """Handle user step."""
    if user_input is None:
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({...}),
            errors=errors,
            description_placeholders={"webhook_url": "..."},
        )

    # Validate and create entry
    return self.async_create_entry(title="...", data={...})

async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
    """Confirmation step."""
    return self.async_show_form(step_id="confirm", ...)

def async_create_entry(self, title: str, data: dict) -> FlowResult:
    """Create config entry."""
    ...

def async_abort(self, reason: str) -> FlowResult:
    """Abort flow."""
    ...

async def async_set_unique_id(self, unique_id: str) -> None:
    """Set unique ID for entry."""
    ...

def _abort_if_unique_id_configured(self) -> None:
    """Abort if unique ID already configured."""
    ...
```

### Config Entry Management
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["binary_sensor"])

# Update config entry
hass.config_entries.async_update_entry(entry, data=new_data)

# Reload config entry
await hass.config_entries.async_reload(entry.entry_id)
```

### Device Info
```python
from homeassistant.helpers.entity import DeviceInfo

DeviceInfo(
    identifiers={(DOMAIN, unique_device_id)},  # Unique per device
    name="Device Name",
    manufacturer="Manufacturer",
    model="Model Name",
    sw_version="1.0.0",
    configuration_url="http://device.local",  # Optional
)
```

### Webhook Management
```python
from homeassistant.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)

# Register
webhook_register(hass, domain, name, webhook_id, handler_function)

# Unregister
webhook_unregister(hass, webhook_id)

# Handler signature
async def handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: aiohttp.web.Request,
) -> None:
    data = await request.json()
    ...
```

---

## Glossary

**Config Entry:** Persistent storage for integration configuration, created via UI config flow

**Config Flow:** UI wizard for setting up an integration

**Options Flow:** UI for modifying integration settings after initial setup

**Device Registry:** HA database of physical devices (cameras, sensors, etc.)

**Entity Registry:** HA database of entities (specific sensors, switches, etc.)

**Unique ID:** Permanent identifier for entity, used to track across restarts

**Entry ID:** Unique identifier for config entry, auto-generated by HA

**Camera ID:** Internal identifier derived from camera name (e.g., "front_door_camera")

**Webhook ID:** Identifier in webhook URL, may be custom or auto-generated

**Platform:** Component type (binary_sensor, sensor, switch, etc.)

**Domain:** Integration identifier ("tplink_vigi")

---

**Document Version:** 1.0
**Last Updated:** 2025-01-17
**Purpose:** Quick reference for implementation

# TP-Link VIGI Integration: UI Configuration Migration Plan

**Last Updated: 2025-01-17**

---

## Executive Summary

This plan outlines the migration of the TP-Link VIGI Home Assistant integration from YAML-only configuration to a modern UI-based configuration flow. The integration currently supports webhook-based event notifications from TP-Link VIGI cameras but requires manual YAML editing. This enhancement will enable users to configure cameras through Home Assistant's UI, improving user experience and following modern Home Assistant best practices.

### Key Objectives
- Implement ConfigFlow for UI-based camera setup
- Add OptionsFlow for managing cameras post-setup
- Create Device entities for proper camera grouping
- Support custom webhook IDs with auto-generation fallback
- Remove YAML configuration support (UI-only approach)
- Maintain backward compatibility for existing webhook endpoints

### Success Criteria
- Users can add/remove/edit cameras via UI
- Each camera appears as a Device with binary sensor entities
- Webhook URLs are clearly displayed during setup
- No breaking changes to webhook functionality
- Zero runtime errors or state corruption

---

## Current State Analysis

### Architecture Overview
```
Current Flow (YAML-based):
1. User edits configuration.yaml
2. HA restart triggers async_setup_platform()
3. Platform reads YAML, generates camera_ids
4. Webhooks registered at /api/webhook/{camera_id}
5. Binary sensor entities created
6. Camera sends POST to webhook
7. Entity updates state
```

### Existing Components

**File: `__init__.py`** (15 lines)
- Minimal integration setup
- Only initializes `hass.data[DOMAIN]` dictionary
- Uses `async_setup()` for YAML support
- NO config entry handling

**File: `binary_sensor.py`** (190 lines)
- Uses `async_setup_platform()` (YAML-based)
- Voluptuous schema validation for YAML
- Webhook registration per camera
- Auto-generates webhook ID from camera name: `name.lower().replace(" ", "_")`
- Binary sensor with 5-second auto-reset
- Stores runtime data in `hass.data[DOMAIN][camera_id]`

**File: `const.py`** (11 lines)
- Domain constant: `"tplink_vigi"`
- CONF_CAMERAS constant
- Event type constants (not enforced)

**File: `manifest.json`**
- Already declares `"config_flow": true` (misleading - not implemented)
- Version 0.0.1, bronze quality scale
- No external dependencies

**Missing Files:**
- `config_flow.py` - NOT IMPLEMENTED
- `strings.json` - NOT IMPLEMENTED
- Device registry integration - NOT IMPLEMENTED

### Current Configuration Model

**YAML Format:**
```yaml
binary_sensor:
  - platform: tplink_vigi
    cameras:
      - name: "Front Door Camera"
      - name: "Backyard Camera"
```

**Runtime Data Structure:**
```python
hass.data[DOMAIN][camera_id] = {
    "name": str,           # "Front Door Camera"
    "is_on": bool,         # True/False
    "last_event": list,    # ["motion", "person"]
    "last_event_time": datetime
}
```

**Webhook Payload:**
```json
{
  "device_name": "Camera Name",
  "ip": "192.168.1.100",
  "mac": "AA:BB:CC:DD:EE:FF",
  "event_list": [{
    "dateTime": "20250117120000",
    "event_type": ["motion", "person"]
  }]
}
```

### Key Observations
1. **Simple Configuration:** Only requires camera name (webhook ID derived)
2. **Stateless Webhooks:** Cameras push data; no polling required
3. **No Device Entities:** Entities are standalone, not grouped
4. **Hardcoded Values:** Reset delay (5s) not configurable
5. **No Validation:** Duplicate names could cause conflicts
6. **No Cleanup:** Webhooks not unregistered on removal

---

## Proposed Future State

### New Architecture
```
New Flow (UI-based):
1. User opens HA UI → Integrations → Add TP-Link VIGI
2. ConfigFlow presents camera name input
3. User optionally customizes webhook ID
4. System displays webhook URL for camera configuration
5. Config entry created with camera data
6. async_setup_entry() called
7. Device + Binary sensor entities created
8. Webhook registered with custom/auto-generated ID
9. User configures camera to POST to displayed URL
10. OptionsFlow allows add/remove/edit cameras
```

### Target Configuration Model

**Config Entry Data:**
```python
{
    "cameras": [
        {
            "name": "Front Door Camera",
            "webhook_id": "front_door_camera",  # User can customize
            "enabled": true
        },
        {
            "name": "Backyard Camera",
            "webhook_id": "backyard_cam",  # Custom ID
            "enabled": true
        }
    ]
}
```

**Device Info:**
```python
DeviceInfo(
    identifiers={(DOMAIN, camera_id)},
    name=camera_name,
    manufacturer="TP-Link",
    model="VIGI Camera",
    sw_version="Unknown",  # Updated from webhook data
)
```

### User Experience Flow

**Initial Setup:**
1. Click "Add Integration" → Search "TP-Link VIGI"
2. Welcome screen explains webhook-based architecture
3. "Add Camera" → Enter name (e.g., "Front Door Camera")
4. Optional: Customize webhook ID (default: `front_door_camera`)
5. Confirmation screen shows:
   - Camera name
   - Webhook URL: `http://YOUR_HA_URL:8123/api/webhook/front_door_camera`
   - Instructions to configure camera
6. Option to "Add Another Camera" or "Finish"

**Managing Cameras (Options Flow):**
1. Navigate to Integration → Click "Configure"
2. See list of configured cameras
3. Actions available:
   - "Add Camera" → Same flow as initial setup
   - "Edit Camera" → Change name/webhook ID (shows warning about URL change)
   - "Remove Camera" → Confirmation dialog

---

## Implementation Phases

### Phase 1: Config Flow Foundation
**Goal:** Implement basic UI configuration for adding cameras

#### Task 1.1: Create config_flow.py Structure (Effort: M)
- Create `custom_components/tplink_vigi/config_flow.py`
- Implement `VigiConfigFlow` class inheriting from `ConfigFlow`
- Set up flow handler registration with `@config_entries.HANDLERS.register(DOMAIN)`
- Add `VERSION = 1` and `MINOR_VERSION = 0` for config entry versioning

**Acceptance Criteria:**
- File created with proper imports
- ConfigFlow class properly registered
- Appears in HA integrations list

**Dependencies:** None

---

#### Task 1.2: Implement Initial Setup Step (Effort: M)
- Implement `async_step_user()` method
- Create data schema with `vol.Schema` for camera name
- Add optional webhook_id field (defaults to auto-generated)
- Implement `_async_generate_webhook_id()` helper method
- Validate no duplicate names or webhook IDs

**Acceptance Criteria:**
- Form displays with name and webhook_id fields
- Webhook ID auto-populates from name
- Validation prevents duplicates
- Error messages display correctly

**Dependencies:** Task 1.1

**Implementation Details:**
```python
async def async_step_user(self, user_input=None):
    errors = {}
    if user_input is not None:
        # Validate input
        name = user_input[CONF_NAME]
        webhook_id = user_input.get(CONF_WEBHOOK_ID) or self._generate_webhook_id(name)

        # Check for duplicates
        await self.async_set_unique_id(webhook_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={"cameras": [{"name": name, "webhook_id": webhook_id}]}
        )

    return self.async_show_form(
        step_id="user",
        data_schema=vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Optional(CONF_WEBHOOK_ID): str,
        }),
        errors=errors,
    )
```

---

#### Task 1.3: Create Webhook URL Display Step (Effort: S)
- Implement `async_step_confirm()` method
- Display generated webhook URL in description placeholders
- Show instructions for configuring camera
- Provide "Add Another" vs "Finish" options

**Acceptance Criteria:**
- Webhook URL clearly displayed
- Instructions easy to understand
- User can add multiple cameras before finishing

**Dependencies:** Task 1.2

---

#### Task 1.4: Add Multi-Camera Support (Effort: M)
- Implement `async_step_add_camera()` method
- Maintain cameras list in config entry data
- Allow adding cameras during initial setup
- Update config entry data with all cameras

**Acceptance Criteria:**
- Can add multiple cameras in one setup flow
- Each camera stored in cameras list
- Flow ends only when user clicks "Finish"

**Dependencies:** Task 1.3

---

### Phase 2: Options Flow Implementation
**Goal:** Enable post-setup camera management

#### Task 2.1: Create Options Flow Handler (Effort: M)
- Implement `async_get_options_flow()` in ConfigFlow
- Create `VigiOptionsFlow` class inheriting from `OptionsFlow`
- Implement `async_step_init()` to show camera list

**Acceptance Criteria:**
- Options menu accessible from integration config
- Displays list of current cameras
- Shows available actions

**Dependencies:** Phase 1 complete

---

#### Task 2.2: Implement Add Camera Option (Effort: M)
- Create `async_step_add_camera()` method
- Reuse camera input form from config flow
- Update config entry data with new camera
- Trigger platform reload to create new entities

**Acceptance Criteria:**
- Can add cameras after initial setup
- New camera appears immediately
- Webhook registered automatically
- Device and entities created

**Dependencies:** Task 2.1

---

#### Task 2.3: Implement Remove Camera Option (Effort: M)
- Create `async_step_remove_camera()` method
- Show confirmation dialog with camera details
- Remove camera from config entry data
- Properly unregister webhook
- Clean up entities and device

**Acceptance Criteria:**
- Camera removed from list
- Webhook unregistered
- Entities removed from HA
- No orphaned data in hass.data

**Dependencies:** Task 2.1

---

#### Task 2.4: Implement Edit Camera Option (Effort: L)
- Create `async_step_edit_camera()` method
- Allow changing name and webhook_id
- Show warning if webhook_id changes
- Update config entry and reload platform

**Acceptance Criteria:**
- Can modify camera name and webhook ID
- Warning displayed for webhook ID changes
- Entities updated with new names
- Old webhook unregistered, new one registered

**Dependencies:** Task 2.1

---

### Phase 3: Integration Entry Point Updates
**Goal:** Migrate from YAML to config entry architecture

#### Task 3.1: Implement async_setup_entry() (Effort: L)
- Add `async_setup_entry()` to `__init__.py`
- Initialize domain data structure
- Store config entry reference in hass.data
- Forward setup to binary_sensor platform
- Return True on success

**Acceptance Criteria:**
- Config entries properly handled
- Domain data initialized
- Platform forwarding works
- No errors during setup

**Dependencies:** Phase 1 complete

**Implementation Details:**
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TP-Link VIGI from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "cameras": {},
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])

    return True
```

---

#### Task 3.2: Implement async_unload_entry() (Effort: M)
- Add `async_unload_entry()` to `__init__.py`
- Unload binary_sensor platform
- Unregister all webhooks for entry
- Clean up hass.data entries
- Return True on success

**Acceptance Criteria:**
- Platform properly unloaded
- Webhooks unregistered
- Memory cleaned up
- No dangling references

**Dependencies:** Task 3.1

**Implementation Details:**
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["binary_sensor"]
    )

    if unload_ok:
        # Unregister webhooks
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if entry_data:
            for camera_id, camera_data in entry_data.get("cameras", {}).items():
                webhook_id = camera_data.get("webhook_id")
                if webhook_id:
                    webhook_unregister(hass, webhook_id)

        # Clean up data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

---

#### Task 3.3: Remove YAML Support (Effort: S)
- Remove or deprecate `async_setup()` from `__init__.py`
- Add comment explaining UI-only configuration
- Update documentation

**Acceptance Criteria:**
- async_setup() removed or returns True without action
- YAML configs no longer processed
- Clear documentation about UI-only approach

**Dependencies:** Task 3.1

---

#### Task 3.4: Add Entry Update Listener (Effort: S)
- Implement `async_update_options()` callback
- Register update listener in async_setup_entry()
- Reload entry when options change

**Acceptance Criteria:**
- Options changes trigger reload
- Cameras update without restart
- No state loss during reload

**Dependencies:** Task 3.1

---

### Phase 4: Binary Sensor Platform Migration
**Goal:** Convert binary_sensor to config entry architecture

#### Task 4.1: Implement async_setup_entry() in Platform (Effort: L)
- Replace `async_setup_platform()` with `async_setup_entry()`
- Read camera list from config entry data
- Create coordinator if needed for shared data
- Remove YAML schema definitions

**Acceptance Criteria:**
- Platform uses config entries, not YAML
- All cameras from entry processed
- Entities created correctly
- Schemas removed

**Dependencies:** Task 3.1

**Implementation Details:**
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from config entry."""
    cameras = entry.data.get("cameras", [])

    sensors = []
    for camera in cameras:
        camera_name = camera["name"]
        webhook_id = camera.get("webhook_id") or camera_name.lower().replace(" ", "_")

        # Store camera data
        camera_id = webhook_id
        hass.data[DOMAIN][entry.entry_id]["cameras"][camera_id] = {
            "name": camera_name,
            "webhook_id": webhook_id,
            "is_on": False,
            "last_event": None,
            "last_event_time": None,
        }

        sensor = VigiCameraBinarySensor(hass, entry, camera_id, camera_name, webhook_id)
        sensors.append(sensor)

        # Register webhook
        webhook_register(
            hass,
            DOMAIN,
            f"VIGI Camera {camera_name}",
            webhook_id,
            sensor.handle_webhook,
        )

        _LOGGER.info(
            "Webhook registered: /api/webhook/%s for camera %s",
            webhook_id,
            camera_name,
        )

    async_add_entities(sensors, True)
```

---

#### Task 4.2: Add Device Registry Integration (Effort: M)
- Import DeviceInfo from homeassistant.helpers.entity
- Add `device_info` property to VigiCameraBinarySensor
- Create device with proper identifiers
- Set manufacturer, model, name

**Acceptance Criteria:**
- Each camera creates a Device entry
- Binary sensor entities grouped under device
- Device shows in HA devices page
- Proper manufacturer/model displayed

**Dependencies:** Task 4.1

**Implementation Details:**
```python
@property
def device_info(self) -> DeviceInfo:
    """Return device info."""
    return DeviceInfo(
        identifiers={(DOMAIN, self._camera_id)},
        name=self._camera_name,
        manufacturer="TP-Link",
        model="VIGI Camera",
        sw_version=self._attributes.get("firmware_version", "Unknown"),
    )
```

---

#### Task 4.3: Update Entity Unique IDs (Effort: S)
- Update unique_id format to include entry_id
- Ensure unique IDs stable across reloads
- Format: `{entry_id}_{camera_id}_motion`

**Acceptance Criteria:**
- Unique IDs unique across entries
- No entity ID conflicts
- Entities survive reload

**Dependencies:** Task 4.1

---

#### Task 4.4: Implement Proper Webhook Cleanup (Effort: M)
- Store webhook_id in entity instance
- Add `async_will_remove_from_hass()` method
- Unregister webhook when entity removed
- Clean up hass.data

**Acceptance Criteria:**
- Webhooks unregistered on entity removal
- No webhook leaks
- Data cleaned up properly

**Dependencies:** Task 4.1

**Implementation Details:**
```python
async def async_will_remove_from_hass(self) -> None:
    """Clean up when entity removed."""
    # Cancel reset task
    if self._reset_task and not self._reset_task.done():
        self._reset_task.cancel()

    # Webhook unregistration handled by platform unload

    # Clean up data
    entry_data = self._hass.data[DOMAIN].get(self._entry.entry_id)
    if entry_data and self._camera_id in entry_data.get("cameras", {}):
        entry_data["cameras"].pop(self._camera_id)
```

---

#### Task 4.5: Update Constructor Signature (Effort: S)
- Add `entry: ConfigEntry` parameter
- Add `webhook_id: str` parameter
- Store references in instance
- Update initialization

**Acceptance Criteria:**
- Constructor accepts entry and webhook_id
- All references properly stored
- No breaking changes to functionality

**Dependencies:** Task 4.1

---

### Phase 5: Constants and Translations
**Goal:** Add proper UI strings and constants

#### Task 5.1: Update const.py (Effort: S)
- Add CONF_WEBHOOK_ID constant
- Add CONF_ENABLED constant
- Add config flow step IDs
- Add error message constants

**Acceptance Criteria:**
- All magic strings moved to constants
- Proper typing for constants
- Well-organized file structure

**Dependencies:** None

**New Constants:**
```python
# Configuration
CONF_WEBHOOK_ID = "webhook_id"
CONF_ENABLED = "enabled"

# Config Flow Steps
STEP_USER = "user"
STEP_CONFIRM = "confirm"
STEP_ADD_CAMERA = "add_camera"
STEP_EDIT_CAMERA = "edit_camera"
STEP_REMOVE_CAMERA = "remove_camera"

# Error Messages
ERROR_DUPLICATE_NAME = "duplicate_name"
ERROR_DUPLICATE_WEBHOOK = "duplicate_webhook"
ERROR_INVALID_WEBHOOK_ID = "invalid_webhook_id"
```

---

#### Task 5.2: Create strings.json (Effort: M)
- Create `custom_components/tplink_vigi/strings.json`
- Add config flow titles and descriptions
- Add step descriptions with webhook URL placeholders
- Add error messages
- Add options flow strings

**Acceptance Criteria:**
- All UI text in strings.json
- Proper placeholders for dynamic values
- Clear, user-friendly language
- No hardcoded strings in code

**Dependencies:** Task 5.1

**strings.json Structure:**
```json
{
  "config": {
    "step": {
      "user": {
        "title": "Add TP-Link VIGI Camera",
        "description": "Configure a VIGI camera to send webhook notifications to Home Assistant.",
        "data": {
          "name": "Camera Name",
          "webhook_id": "Webhook ID (optional)"
        }
      },
      "confirm": {
        "title": "Camera Added Successfully",
        "description": "Configure your camera to send events to:\n\n`{webhook_url}`\n\nWould you like to add another camera?"
      }
    },
    "error": {
      "duplicate_name": "A camera with this name already exists",
      "duplicate_webhook": "This webhook ID is already in use",
      "invalid_webhook_id": "Webhook ID can only contain lowercase letters, numbers, and underscores"
    },
    "abort": {
      "already_configured": "This webhook ID is already configured"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Manage VIGI Cameras",
        "description": "Add, edit, or remove cameras",
        "menu_options": {
          "add_camera": "Add Camera",
          "edit_camera": "Edit Camera",
          "remove_camera": "Remove Camera"
        }
      }
    }
  }
}
```

---

#### Task 5.3: Create translations Directory (Effort: S)
- Create `custom_components/tplink_vigi/translations/` directory
- Copy strings.json to `translations/en.json`
- Add translation structure for future localization

**Acceptance Criteria:**
- translations/en.json exists
- Matches strings.json content
- Ready for additional languages

**Dependencies:** Task 5.2

---

### Phase 6: Testing and Validation
**Goal:** Ensure all functionality works correctly

#### Task 6.1: Manual Config Flow Testing (Effort: M)
- Test adding first camera via UI
- Test adding multiple cameras in one flow
- Test webhook URL display
- Test duplicate name validation
- Test custom webhook ID
- Verify entities created correctly

**Acceptance Criteria:**
- All user flows work without errors
- Validation catches invalid input
- Webhook URLs correct and accessible
- Entities appear in UI

**Dependencies:** Phases 1-5 complete

**Test Cases:**
1. Add camera with auto-generated webhook ID
2. Add camera with custom webhook ID
3. Try to add duplicate camera name (should fail)
4. Try to add duplicate webhook ID (should fail)
5. Add 3 cameras in single setup flow
6. Verify all webhooks registered
7. Test webhook with curl POST

---

#### Task 6.2: Manual Options Flow Testing (Effort: M)
- Test adding camera via options
- Test editing camera name
- Test editing webhook ID (verify warning)
- Test removing camera
- Verify webhook cleanup

**Acceptance Criteria:**
- Can add cameras post-setup
- Edits apply correctly
- Warnings shown when appropriate
- Removals clean up properly
- No orphaned webhooks or entities

**Dependencies:** Task 6.1

**Test Cases:**
1. Add camera via options flow
2. Edit camera name only
3. Edit webhook ID (verify warning and URL change)
4. Remove camera (verify webhook unregistered)
5. Reload HA and verify config persists
6. Remove all cameras then re-add

---

#### Task 6.3: Webhook Functionality Testing (Effort: M)
- Send test webhooks to each camera
- Verify binary sensor state changes
- Verify attributes populated correctly
- Verify auto-reset after 5 seconds
- Test multiple rapid events
- Test malformed payloads

**Acceptance Criteria:**
- Webhooks trigger state changes
- Attributes show correct data
- Auto-reset works reliably
- No crashes on bad data
- Multiple events handled correctly

**Dependencies:** Task 6.1

**Test Script:**
```bash
# Test webhook
curl -X POST http://localhost:8123/api/webhook/front_door_camera \
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

---

#### Task 6.4: Device Registry Validation (Effort: S)
- Verify devices appear in device registry
- Check device info correct (manufacturer, model)
- Verify entities grouped under device
- Test device renaming
- Test device removal

**Acceptance Criteria:**
- All cameras show as devices
- Device info accurate
- Entities properly grouped
- Device operations work correctly

**Dependencies:** Task 6.1

---

#### Task 6.5: Entry Lifecycle Testing (Effort: M)
- Test config entry reload
- Test integration removal
- Test re-adding after removal
- Test HA restart with config
- Verify no memory leaks
- Check logs for errors

**Acceptance Criteria:**
- Reload works without issues
- Removal cleans up completely
- Can re-add after removal
- Survives HA restart
- No memory leaks detected
- Clean logs (no errors/warnings)

**Dependencies:** Tasks 6.1, 6.2

**Test Procedure:**
1. Add 3 cameras
2. Reload integration
3. Verify cameras still work
4. Remove integration
5. Check webhooks unregistered
6. Check entities removed
7. Re-add integration
8. Add cameras again
9. Restart HA
10. Verify cameras restored

---

#### Task 6.6: Error Handling Validation (Effort: S)
- Test invalid webhook payloads
- Test missing required fields
- Test malformed datetime
- Test network errors (if applicable)
- Verify graceful error handling
- Check error logging

**Acceptance Criteria:**
- Invalid data doesn't crash system
- Errors logged appropriately
- User-friendly error messages
- System remains stable

**Dependencies:** Task 6.3

---

### Phase 7: Documentation and Polish
**Goal:** Complete documentation and final refinements

#### Task 7.1: Update CLAUDE.md (Effort: M)
- Document new config flow architecture
- Update configuration examples (remove YAML)
- Add device registry info
- Document webhook ID customization
- Update testing instructions

**Acceptance Criteria:**
- CLAUDE.md reflects new architecture
- All examples updated
- Clear migration notes
- Testing docs updated

**Dependencies:** Phase 6 complete

---

#### Task 7.2: Add Code Comments and Docstrings (Effort: S)
- Add comprehensive docstrings to all methods
- Add inline comments for complex logic
- Document webhook payload format
- Add type hints everywhere

**Acceptance Criteria:**
- All public methods have docstrings
- Complex code has comments
- Type hints complete
- Code self-documenting

**Dependencies:** Phases 1-5 complete

---

#### Task 7.3: Code Quality Review (Effort: M)
- Run ruff linter
- Run mypy type checker
- Fix any linting issues
- Ensure consistent code style
- Remove debug logging

**Acceptance Criteria:**
- No linter errors
- No type checker errors
- Consistent style
- Production-ready code

**Dependencies:** Task 7.2

---

#### Task 7.4: Create Migration Guide (Effort: S)
- Document how to migrate from YAML (if needed)
- Create user-facing setup instructions
- Add troubleshooting section
- Include webhook testing examples

**Acceptance Criteria:**
- Clear migration instructions
- Setup guide complete
- Common issues documented
- Examples provided

**Dependencies:** Phase 6 complete

---

## Risk Assessment and Mitigation Strategies

### Risk 1: Breaking Existing Webhooks
**Severity:** HIGH
**Probability:** MEDIUM

**Description:** Changing webhook registration could break existing camera configurations.

**Mitigation:**
- Maintain same webhook URL format (`/api/webhook/{camera_id}`)
- Default webhook_id to same algorithm (name.lower().replace(" ", "_"))
- Test with existing webhook payloads
- Document any required camera reconfiguration

**Contingency:**
- Add YAML import flow to auto-migrate existing configs
- Provide webhook ID override for backward compatibility

---

### Risk 2: Webhook Cleanup Failures
**Severity:** MEDIUM
**Probability:** MEDIUM

**Description:** Webhooks may not unregister properly, causing conflicts or memory leaks.

**Mitigation:**
- Implement proper `async_unload_entry()`
- Add `async_will_remove_from_hass()` to entities
- Test removal scenarios thoroughly
- Add logging for webhook lifecycle

**Contingency:**
- Add manual webhook cleanup utility
- Implement webhook health check
- Add HA restart as nuclear option

---

### Risk 3: Data Structure Migration Issues
**Severity:** MEDIUM
**Probability:** LOW

**Description:** Moving from YAML to config entries changes data storage, potentially causing issues.

**Mitigation:**
- Keep same runtime data structure in hass.data
- Use config entry ID as namespace
- Test reload and restart scenarios
- Maintain backward compatibility where possible

**Contingency:**
- Add data migration utility
- Implement fallback to legacy structure
- Provide manual recovery steps

---

### Risk 4: Duplicate Webhook IDs
**Severity:** HIGH
**Probability:** LOW

**Description:** Users could create duplicate webhook IDs, causing conflicts.

**Mitigation:**
- Validate webhook IDs for uniqueness
- Use ConfigEntry unique_id mechanism
- Show clear error messages
- Suggest alternative IDs

**Contingency:**
- Implement auto-suffix for duplicates (e.g., camera_2)
- Add webhook ID conflict resolution flow
- Allow force override with warning

---

### Risk 5: Device/Entity Orphaning
**Severity:** MEDIUM
**Probability:** MEDIUM

**Description:** Removing cameras may leave orphaned devices or entities.

**Mitigation:**
- Properly implement entity removal
- Clean up device registry entries
- Test removal thoroughly
- Add cleanup verification

**Contingency:**
- Add manual cleanup utility
- Document manual device removal steps
- Implement "repair" flow to clean orphans

---

### Risk 6: Options Flow State Management
**Severity:** LOW
**Probability:** MEDIUM

**Description:** Complex options flow could lead to inconsistent state.

**Mitigation:**
- Keep options flow simple and linear
- Validate all changes before applying
- Test edge cases thoroughly
- Implement rollback on errors

**Contingency:**
- Add "reset to defaults" option
- Allow direct config entry editing
- Provide HA restart as recovery

---

## Success Metrics

### Functional Metrics
- ✅ 100% of config flow paths tested and working
- ✅ 100% of options flow paths tested and working
- ✅ 0 errors in Home Assistant logs during normal operation
- ✅ All devices show in device registry with correct info
- ✅ All webhook URLs accessible and functional

### Quality Metrics
- ✅ 0 linter errors (ruff)
- ✅ 0 type checker errors (mypy)
- ✅ All public methods have docstrings
- ✅ Code coverage >80% (if tests added)

### User Experience Metrics
- ✅ Setup completable in <2 minutes
- ✅ Webhook URL clearly displayed and copyable
- ✅ All error messages clear and actionable
- ✅ No HA restart required for any operation
- ✅ Documentation complete and understandable

### Performance Metrics
- ✅ Config flow loads in <1 second
- ✅ Webhook response time <100ms
- ✅ No memory leaks after 1000 events
- ✅ Integration reload in <2 seconds

---

## Required Resources and Dependencies

### Technical Dependencies
- Home Assistant Core 2024.1.0+ (for latest ConfigFlow APIs)
- Python 3.11+ (for type hints and async features)
- No external Python packages required

### Knowledge Requirements
- Home Assistant ConfigFlow architecture
- Home Assistant Device Registry
- Webhook handling in Home Assistant
- Python async programming
- Voluptuous schema validation

### Development Environment
- Home Assistant development instance
- TP-Link VIGI camera (or webhook simulator)
- Code editor with Python support
- Git for version control

### Testing Resources
- Home Assistant test instance
- curl or Postman for webhook testing
- Multiple test cameras (or simulated webhooks)
- HA logs monitoring tool

---

## Timeline Estimates

### Conservative Estimate (Single Developer)
- **Phase 1:** 8-12 hours (Config Flow Foundation)
- **Phase 2:** 6-10 hours (Options Flow)
- **Phase 3:** 4-6 hours (Integration Entry Point)
- **Phase 4:** 8-12 hours (Binary Sensor Migration)
- **Phase 5:** 2-4 hours (Constants and Translations)
- **Phase 6:** 8-12 hours (Testing and Validation)
- **Phase 7:** 3-5 hours (Documentation)

**Total:** 39-61 hours (5-8 working days)

### Aggressive Estimate (Experienced Developer)
- **Phase 1:** 4-6 hours
- **Phase 2:** 3-5 hours
- **Phase 3:** 2-3 hours
- **Phase 4:** 4-6 hours
- **Phase 5:** 1-2 hours
- **Phase 6:** 4-6 hours
- **Phase 7:** 2-3 hours

**Total:** 20-31 hours (3-4 working days)

### Recommended Approach
Work in phases with validation gates. Complete and test each phase before moving to next. This prevents cascading issues and makes debugging easier.

**Milestone Schedule:**
- Week 1: Phases 1-3 (Config flow and entry points)
- Week 2: Phases 4-5 (Platform migration and UI)
- Week 3: Phases 6-7 (Testing and documentation)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up development environment** with HA test instance
3. **Begin Phase 1** - Config Flow Foundation
4. **Commit frequently** with descriptive messages
5. **Test incrementally** after each task
6. **Document as you go** to avoid catch-up at the end
7. **Seek code review** after each phase for early feedback

---

## Appendix: Key Implementation Snippets

### Config Entry Data Schema
```python
{
    "cameras": [
        {
            "name": str,          # "Front Door Camera"
            "webhook_id": str,    # "front_door_camera"
            "enabled": bool,      # true
        }
    ]
}
```

### Runtime Data Structure
```python
hass.data[DOMAIN][entry.entry_id] = {
    "entry": ConfigEntry,
    "cameras": {
        camera_id: {
            "name": str,
            "webhook_id": str,
            "is_on": bool,
            "last_event": list[str],
            "last_event_time": datetime,
        }
    }
}
```

### Webhook ID Generation
```python
def _generate_webhook_id(name: str) -> str:
    """Generate webhook ID from camera name."""
    return name.lower().replace(" ", "_")
```

### Webhook URL Format
```
http://{ha_url}:8123/api/webhook/{webhook_id}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-01-17
**Status:** Ready for Implementation

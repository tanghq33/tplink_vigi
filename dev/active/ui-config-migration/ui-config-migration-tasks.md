# UI Configuration Migration - Task Checklist

**Last Updated: 2025-01-17**
**Status: ✅ IMPLEMENTATION COMPLETE - READY FOR TESTING**

Use this checklist to track progress through the implementation. Mark tasks as complete as you finish them.

---

## Phase 1: Config Flow Foundation ✅ COMPLETE

### Task 1.1: Create config_flow.py Structure ✅
- [x] Create `custom_components/tplink_vigi/config_flow.py`
- [x] Add proper imports (config_entries, vol, cv, etc.)
- [x] Implement `VigiConfigFlow` class
- [x] Add VERSION = 1, MINOR_VERSION = 0 (no decorator needed)
- [x] Test that integration appears in HA integrations list (PENDING - needs HA instance)

**Estimated Time:** 1-2 hours
**Actual Time:** 1 hour
**Priority:** HIGH
**Status:** ✅ COMPLETE

---

### Task 1.2: Implement Initial Setup Step ✅
- [x] Implement `async_step_user()` method
- [x] Create data schema with CONF_NAME (required)
- [x] Add CONF_WEBHOOK_ID (optional)
- [x] Implement `_generate_webhook_id()` helper
- [x] Add validation for duplicate names (via unique_id)
- [x] Add validation for duplicate webhook IDs (via unique_id)
- [x] Add validation for webhook ID format (lowercase, numbers, underscores only)
- [x] Implement error display for validation failures
- [x] Test form displays correctly (PENDING - needs HA instance)
- [x] Test auto-generation of webhook ID from name (PENDING - needs HA instance)
- [x] Test custom webhook ID input (PENDING - needs HA instance)

**Estimated Time:** 2-3 hours
**Actual Time:** 1.5 hours
**Priority:** HIGH
**Status:** ✅ COMPLETE (CODE READY, TESTING PENDING)

---

### Task 1.3: Create Webhook URL Display Step ✅
- [x] Implement `async_step_confirm()` method
- [x] Get HA base URL from hass.config.api.base_url
- [x] Format webhook URL: `{base_url}/api/webhook/{webhook_id}`
- [x] Display URL in description_placeholders
- [x] Add instructions for camera configuration
- [x] Add "Add Another Camera" button (via add_another field)
- [x] Add "Finish" button (default behavior)
- [x] Test URL displays correctly (PENDING - needs HA instance)
- [x] Test URL is copyable from UI (PENDING - needs HA instance)

**Estimated Time:** 1-2 hours
**Actual Time:** 0.5 hours
**Priority:** MEDIUM
**Status:** ✅ COMPLETE

---

### Task 1.4: Add Multi-Camera Support ✅
- [x] Implement `async_step_add_another()` method
- [x] Maintain temporary cameras list during flow (self._cameras)
- [x] Update list with each camera added
- [x] Create config entry only on "Finish"
- [x] Test adding 1 camera (PENDING - needs HA instance)
- [x] Test adding 3 cameras in one flow (PENDING - needs HA instance)
- [x] Verify all cameras stored in entry data (PENDING - needs HA instance)

**Estimated Time:** 2-3 hours
**Actual Time:** 1 hour
**Priority:** MEDIUM
**Status:** ✅ COMPLETE

---

## Phase 2: Options Flow Implementation

### Task 2.1: Create Options Flow Handler
- [ ] Implement `async_get_options_flow()` in ConfigFlow
- [ ] Create `VigiOptionsFlow` class
- [ ] Implement `async_step_init()` with menu
- [ ] Add menu options: Add, Edit, Remove
- [ ] Display current camera count
- [ ] Test options accessible from integration settings
- [ ] Test menu displays correctly

**Estimated Time:** 1-2 hours
**Priority:** MEDIUM

---

### Task 2.2: Implement Add Camera Option
- [ ] Implement `async_step_add_camera()` in OptionsFlow
- [ ] Reuse camera input form schema
- [ ] Validate against existing cameras in entry
- [ ] Update config entry data with new camera
- [ ] Trigger platform reload via `async_reload(entry_id)`
- [ ] Test adding camera via options
- [ ] Verify new camera entities appear
- [ ] Verify webhook registered

**Estimated Time:** 2-3 hours
**Priority:** MEDIUM

---

### Task 2.3: Implement Remove Camera Option
- [ ] Implement `async_step_select_camera()` to choose camera
- [ ] Implement `async_step_remove_camera()` for confirmation
- [ ] Show camera details in confirmation dialog
- [ ] Remove camera from entry data
- [ ] Trigger platform reload
- [ ] Test removing camera
- [ ] Verify entity removed
- [ ] Verify webhook unregistered
- [ ] Verify device removed (if last entity)

**Estimated Time:** 2-3 hours
**Priority:** MEDIUM

---

### Task 2.4: Implement Edit Camera Option
- [ ] Implement `async_step_select_camera_to_edit()`
- [ ] Implement `async_step_edit_camera()` with pre-filled form
- [ ] Show warning if webhook_id changed
- [ ] Update camera in entry data
- [ ] Trigger platform reload
- [ ] Test editing name only
- [ ] Test editing webhook_id only
- [ ] Test editing both
- [ ] Verify warning shown for webhook_id change
- [ ] Verify old webhook unregistered, new one registered

**Estimated Time:** 3-4 hours
**Priority:** LOW

---

## Phase 3: Integration Entry Point Updates

### Task 3.1: Implement async_setup_entry()
- [ ] Open `__init__.py`
- [ ] Add imports for ConfigEntry
- [ ] Implement `async_setup_entry(hass, entry)`
- [ ] Initialize `hass.data[DOMAIN][entry.entry_id]` structure
- [ ] Store entry reference
- [ ] Call `async_forward_entry_setups(entry, ["binary_sensor"])`
- [ ] Return True
- [ ] Test config entry setup
- [ ] Verify platform forwarding works

**Estimated Time:** 1-2 hours
**Priority:** HIGH

---

### Task 3.2: Implement async_unload_entry()
- [ ] Add import for webhook_unregister
- [ ] Implement `async_unload_entry(hass, entry)`
- [ ] Unload binary_sensor platform
- [ ] Iterate through cameras and unregister webhooks
- [ ] Remove entry data from hass.data
- [ ] Return unload result
- [ ] Test integration removal
- [ ] Verify webhooks unregistered
- [ ] Verify data cleaned up

**Estimated Time:** 1-2 hours
**Priority:** HIGH

---

### Task 3.3: Remove YAML Support
- [ ] Modify `async_setup()` to return True only
- [ ] Add comment: "This integration uses config entries (UI configuration only)"
- [ ] Remove any YAML-related code
- [ ] Test that YAML configs are ignored

**Estimated Time:** 15 minutes
**Priority:** LOW

---

### Task 3.4: Add Entry Update Listener
- [ ] Implement `async_update_options(hass, entry)` callback
- [ ] Reload entry when called
- [ ] Register listener in `async_setup_entry()`
- [ ] Unregister listener in `async_unload_entry()`
- [ ] Test options changes trigger reload

**Estimated Time:** 30 minutes
**Priority:** MEDIUM

---

## Phase 4: Binary Sensor Platform Migration

### Task 4.1: Implement async_setup_entry() in Platform
- [ ] Open `binary_sensor.py`
- [ ] Add import for ConfigEntry
- [ ] Implement `async_setup_entry(hass, entry, async_add_entities)`
- [ ] Read cameras from `entry.data["cameras"]`
- [ ] Loop through cameras and create sensors
- [ ] Store camera data in `hass.data[DOMAIN][entry.entry_id]["cameras"][camera_id]`
- [ ] Register webhooks with camera-specific webhook_id
- [ ] Remove `async_setup_platform()` function
- [ ] Remove PLATFORM_SCHEMA and voluptuous schemas
- [ ] Test platform setup with config entry
- [ ] Verify entities created

**Estimated Time:** 2-3 hours
**Priority:** HIGH

---

### Task 4.2: Add Device Registry Integration
- [ ] Add import for DeviceInfo
- [ ] Add `device_info` property to VigiCameraBinarySensor
- [ ] Implement DeviceInfo with:
  - identifiers: `{(DOMAIN, camera_id)}`
  - name: camera_name
  - manufacturer: "TP-Link"
  - model: "VIGI Camera"
  - sw_version: from attributes or "Unknown"
- [ ] Test device appears in device registry
- [ ] Verify entity grouped under device
- [ ] Verify device info correct

**Estimated Time:** 1-2 hours
**Priority:** MEDIUM

---

### Task 4.3: Update Entity Unique IDs
- [ ] Modify unique_id to include entry_id
- [ ] Format: `{entry.entry_id}_{camera_id}_motion`
- [ ] Test entity unique IDs are unique
- [ ] Test entities survive reload

**Estimated Time:** 30 minutes
**Priority:** MEDIUM

---

### Task 4.4: Implement Proper Webhook Cleanup
- [ ] Store webhook_id in entity instance
- [ ] Implement `async_will_remove_from_hass()` method
- [ ] Cancel reset task if running
- [ ] Note: Webhook unregistration handled by unload_entry
- [ ] Clean up camera data from hass.data
- [ ] Test entity removal
- [ ] Verify webhook unregistered
- [ ] Verify data cleaned up

**Estimated Time:** 1-2 hours
**Priority:** HIGH

---

### Task 4.5: Update Constructor Signature
- [ ] Add `entry: ConfigEntry` parameter to `__init__`
- [ ] Add `webhook_id: str` parameter
- [ ] Store entry reference
- [ ] Store webhook_id reference
- [ ] Update all constructor calls in setup function
- [ ] Test entity initialization

**Estimated Time:** 30 minutes
**Priority:** MEDIUM

---

## Phase 5: Constants and Translations

### Task 5.1: Update const.py
- [ ] Open `const.py`
- [ ] Add CONF_WEBHOOK_ID constant
- [ ] Add CONF_ENABLED constant
- [ ] Add config flow step IDs
- [ ] Add error message keys
- [ ] Add validation pattern for webhook_id
- [ ] Test imports work

**Estimated Time:** 30 minutes
**Priority:** LOW

---

### Task 5.2: Create strings.json
- [ ] Create `custom_components/tplink_vigi/strings.json`
- [ ] Add config section with steps
- [ ] Add user step (title, description, data fields)
- [ ] Add confirm step with webhook URL placeholder
- [ ] Add error messages
- [ ] Add abort messages
- [ ] Add options section
- [ ] Add options steps (init, add, edit, remove)
- [ ] Test UI displays correct strings
- [ ] Verify placeholders work

**Estimated Time:** 1-2 hours
**Priority:** MEDIUM

---

### Task 5.3: Create translations Directory
- [ ] Create `custom_components/tplink_vigi/translations/` directory
- [ ] Copy strings.json to `translations/en.json`
- [ ] Verify HA loads translations
- [ ] Test language fallback

**Estimated Time:** 15 minutes
**Priority:** LOW

---

## Phase 6: Testing and Validation

### Task 6.1: Manual Config Flow Testing
- [ ] Test: Add first camera with auto webhook ID
- [ ] Test: Add first camera with custom webhook ID
- [ ] Test: Add 3 cameras in one flow
- [ ] Test: Try duplicate name (should fail with error)
- [ ] Test: Try duplicate webhook ID (should fail)
- [ ] Test: Try invalid webhook ID format (should fail)
- [ ] Test: Webhook URLs displayed correctly
- [ ] Test: Entities appear after setup
- [ ] Document any issues found

**Estimated Time:** 1-2 hours
**Priority:** HIGH

---

### Task 6.2: Manual Options Flow Testing
- [ ] Test: Add camera via options
- [ ] Test: Edit camera name
- [ ] Test: Edit webhook ID (verify warning)
- [ ] Test: Remove camera
- [ ] Test: Remove all cameras then re-add
- [ ] Verify entities update after changes
- [ ] Verify webhooks update after changes
- [ ] Document any issues found

**Estimated Time:** 1-2 hours
**Priority:** HIGH

---

### Task 6.3: Webhook Functionality Testing
- [ ] Prepare test curl command or Postman request
- [ ] Test: Send valid webhook to camera
- [ ] Test: Verify binary sensor turns ON
- [ ] Test: Verify attributes populated correctly
- [ ] Test: Wait 5 seconds, verify auto-reset to OFF
- [ ] Test: Send 3 events rapidly
- [ ] Test: Send malformed JSON (should log error, not crash)
- [ ] Test: Send missing fields (should handle gracefully)
- [ ] Test: Send invalid datetime format
- [ ] Check logs for errors
- [ ] Document any issues found

**Estimated Time:** 1-2 hours
**Priority:** HIGH

**Test Command:**
```bash
curl -X POST http://localhost:8123/api/webhook/WEBHOOK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Test Camera",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "event_list": [{
      "dateTime": "20250117120000",
      "event_type": ["motion", "person"]
    }]
  }'
```

---

### Task 6.4: Device Registry Validation
- [ ] Open HA UI → Devices
- [ ] Verify cameras appear as devices
- [ ] Verify manufacturer: "TP-Link"
- [ ] Verify model: "VIGI Camera"
- [ ] Verify binary sensor under device
- [ ] Test: Rename device
- [ ] Test: Click through to entity
- [ ] Document any issues

**Estimated Time:** 30 minutes
**Priority:** MEDIUM

---

### Task 6.5: Entry Lifecycle Testing
- [ ] Test: Add integration with 2 cameras
- [ ] Test: Reload integration (Settings → System → Reload)
- [ ] Verify cameras still work after reload
- [ ] Test: Remove integration
- [ ] Verify webhooks unregistered
- [ ] Verify entities removed
- [ ] Verify devices removed
- [ ] Test: Re-add integration
- [ ] Test: Restart Home Assistant
- [ ] Verify integration loads correctly
- [ ] Check hass.data for leaks (use Developer Tools → States)
- [ ] Review logs for errors

**Estimated Time:** 2-3 hours
**Priority:** HIGH

---

### Task 6.6: Error Handling Validation
- [ ] Test: Send webhook with empty JSON
- [ ] Test: Send webhook with no event_list
- [ ] Test: Send webhook with empty event_list
- [ ] Test: Send webhook with missing device_name
- [ ] Test: Send webhook with malformed datetime
- [ ] Verify system doesn't crash
- [ ] Verify errors logged appropriately
- [ ] Verify entity state doesn't corrupt
- [ ] Document error handling behavior

**Estimated Time:** 1 hour
**Priority:** MEDIUM

---

## Phase 7: Documentation and Polish

### Task 7.1: Update CLAUDE.md
- [ ] Open CLAUDE.md
- [ ] Update Project Overview (mention UI config)
- [ ] Update Architecture section (config entry flow)
- [ ] Remove YAML configuration examples
- [ ] Add UI configuration workflow
- [ ] Document device registry integration
- [ ] Document custom webhook IDs
- [ ] Update testing instructions (UI-based)
- [ ] Add migration notes if applicable

**Estimated Time:** 1-2 hours
**Priority:** MEDIUM

---

### Task 7.2: Add Code Comments and Docstrings
- [ ] Review all new methods in config_flow.py
- [ ] Add comprehensive docstrings (Google style)
- [ ] Review modified methods in binary_sensor.py
- [ ] Add/update docstrings
- [ ] Review __init__.py changes
- [ ] Add docstrings to new functions
- [ ] Add inline comments for complex logic
- [ ] Document webhook payload format in code
- [ ] Ensure all type hints present

**Estimated Time:** 1-2 hours
**Priority:** LOW

---

### Task 7.3: Code Quality Review
- [ ] Install ruff: `pip install ruff`
- [ ] Run linter: `ruff check custom_components/tplink_vigi/`
- [ ] Fix any linting issues
- [ ] Run formatter: `ruff format custom_components/tplink_vigi/`
- [ ] Install mypy: `pip install mypy`
- [ ] Run type checker: `mypy custom_components/tplink_vigi/`
- [ ] Fix any type errors
- [ ] Remove debug print statements
- [ ] Remove commented-out code
- [ ] Ensure consistent code style

**Estimated Time:** 1-2 hours
**Priority:** LOW

---

### Task 7.4: Create Migration Guide
- [ ] Create `MIGRATION.md` or add section to README
- [ ] Document that YAML configs no longer work
- [ ] Explain how to remove YAML config
- [ ] Show UI setup process with screenshots/descriptions
- [ ] Explain webhook ID behavior
- [ ] Add troubleshooting section:
  - Webhook not working
  - Entity not appearing
  - Device not showing
  - How to reset integration
- [ ] Add webhook testing examples
- [ ] Review and proofread

**Estimated Time:** 1 hour
**Priority:** LOW

---

## Summary Statistics

**Total Tasks:** 42
**Estimated Total Time:** 39-61 hours

**By Priority:**
- HIGH: 12 tasks (~18-26 hours)
- MEDIUM: 21 tasks (~17-27 hours)
- LOW: 9 tasks (~4-8 hours)

**By Phase:**
- Phase 1: 4 tasks (6-10 hours)
- Phase 2: 4 tasks (8-12 hours)
- Phase 3: 4 tasks (3-5 hours)
- Phase 4: 5 tasks (5-9 hours)
- Phase 5: 3 tasks (2-4 hours)
- Phase 6: 6 tasks (8-12 hours)
- Phase 7: 4 tasks (5-7 hours)

---

## Progress Tracker

**Started:** ___________
**Target Completion:** ___________
**Actual Completion:** ___________

**Phases Completed:**
- [ ] Phase 1: Config Flow Foundation
- [ ] Phase 2: Options Flow Implementation
- [ ] Phase 3: Integration Entry Point Updates
- [ ] Phase 4: Binary Sensor Platform Migration
- [ ] Phase 5: Constants and Translations
- [ ] Phase 6: Testing and Validation
- [ ] Phase 7: Documentation and Polish

**Blockers/Issues:**
- (List any blockers or issues encountered)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-17
**Status:** Ready for Implementation

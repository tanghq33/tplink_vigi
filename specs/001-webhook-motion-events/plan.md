# Implementation Plan: TPLink Vigi Webhook Motion Detection

**Branch**: `001-webhook-motion-events` | **Date**: 2025-11-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-webhook-motion-events/spec.md`

## Summary

Create a Home Assistant custom integration for TPLink Vigi cameras that receives motion detection events via webhooks. Each integration instance manages one camera with a unique auto-generated UUID webhook endpoint. The integration creates a device with binary sensor (motion detection) and image entity (last captured image), supporting both JSON and multipart form webhook payloads. Only the most recent event and image are retained.

## Current Implementation Analysis

### Existing Implementation

The integration currently has a **partial implementation** with the following components:

**Implemented Features:**
- ✅ Config flow for adding cameras (config_flow.py)
- ✅ Options flow for editing camera settings
- ✅ Webhook registration per camera
- ✅ Binary sensor for motion detection (binary_sensor.py)
- ✅ Webhook handling with JSON payload support
- ✅ Auto-reset to clear state after configurable timeout
- ✅ Device creation with proper DeviceInfo
- ✅ Proper entity naming and unique IDs
- ✅ Webhook deregistration on unload
- ✅ Multi-camera support (multiple integration instances)
- ✅ Stable camera_id (UUID) for device identity
- ✅ Translations (strings.json, en.json)

**Partially Implemented:**
- ⚠️ Webhook ID is user-editable (spec requires auto-generated UUID, non-editable)
- ⚠️ Webhook URL display exists but could be improved in options flow
- ⚠️ JSON webhook payload handling exists but needs validation against spec requirements

**Missing/Gaps vs Specification:**
- ❌ **FR-002, FR-003**: Webhook ID is currently user-editable; spec requires auto-generated random UUID that cannot be edited
- ❌ **FR-008**: No image entity implementation (stores/displays last captured image)
- ❌ **FR-010**: No multipart form payload support (only JSON currently supported)
- ❌ **FR-012**: No image update handling in webhook
- ❌ **FR-014**: No image storage/replacement logic
- ❌ **FR-027**: No Home Assistant image entity for displaying captured images
- ❌ **Type annotations**: Missing comprehensive type hints (constitution requirement)
- ❌ **Error handling**: Generic exception catching (BLE001) instead of specific exception types
- ❌ **Logging**: Insufficient structured logging with context

### Constitution Compliance Gaps

1. **Type Safety**: Partial compliance - type hints exist but not comprehensive
2. **Defensive Error Handling**: Needs improvement - using generic `Exception` catching
3. **UX Consistency**: Good - follows HA conventions
4. **Performance**: Good - async operations used properly
5. **HA Standards**: Good - proper structure, no tests yet

## Technical Context

**Language/Version**: Python 3.11+ (Home Assistant 2024+ requirement)
**Primary Dependencies**: Home Assistant Core (homeassistant), aiohttp (built-in HA HTTP client)
**Storage**: Home Assistant config entries (no external database), in-memory state for current event/image
**Testing**: pytest with pytest-homeassistant-custom-component (standard HA testing framework)
**Target Platform**: Home Assistant OS / Container / Core (cross-platform Python)
**Project Type**: Home Assistant custom component (single integration structure)
**Performance Goals**:
- Webhook response <1s (p95) per SC-002
- Image processing <3s per SC-003
- Support 10+ concurrent cameras per SC-004
- No event loop blocking >50ms per constitution
**Constraints**:
- Must follow HA integration patterns
- Config entries only (no YAML)
- Async-first design
- Memory-efficient (retain only last image)
**Scale/Scope**:
- Single camera per integration instance
- Up to 10-20 cameras total per HA instance (realistic home deployment)
- Images up to 5MB (typical camera snapshot size)
- Webhook events max once per second (camera hardware limit)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Type Safety & Static Analysis

**Status**: ⚠️ PARTIAL COMPLIANCE - Needs improvement

**Current State:**
- Type hints present on most function signatures
- Missing type hints on some class attributes
- No mypy configuration or CI enforcement
- No type:ignore comments (good)

**Required Actions:**
- Add comprehensive type annotations to all functions, methods, class attributes
- Add mypy configuration file (mypy.ini or pyproject.toml)
- Add type annotations to webhook handler data extraction
- Ensure all dict/list types specify contents (dict[str, Any], list[str], etc.)

### II. Defensive Error Handling

**Status**: ⚠️ PARTIAL COMPLIANCE - Needs significant improvement

**Current State:**
- Generic `except Exception` used with # noqa: BLE001 (too broad)
- Some try/except blocks present but not comprehensive
- Logging exists but lacks structured context
- Some edge cases handled (duplicate webhooks, invalid IDs)

**Required Actions per Specification:**
- FR-021: Network interruption during image transmission → log warning, continue
- FR-022: Malformed data/unexpected payloads → log warning with details, continue
- FR-023: Oversized images → log warning with size, continue
- Replace generic `Exception` with specific exception types (ValueError, KeyError, asyncio.TimeoutError, etc.)
- Add _LOGGER.error() with full context (device ID, operation, exception details)
- Add _LOGGER.warning() for edge cases (malformed data, size limits)
- Validate all input data before use (None checks, type checks, range validation)

### III. User Experience Consistency

**Status**: ✅ COMPLIANT

**Current State:**
- Entity naming follows "[Camera Name] Motion" pattern
- Stable unique IDs using camera_id UUID
- Config flow with proper validation
- Options flow for reconfiguration
- Device class set to MOTION
- Snake_case attributes

**Observations:**
- Good adherence to HA conventions
- Webhook URL display in confirmation step
- Clear error messages in translations

###IV. Performance & Resource Efficiency

**Status**: ✅ COMPLIANT

**Current State:**
- All I/O operations are async
- Webhook handler is async
- Reset delay is configurable (default 5s, range 1-60s)
- Cleanup on unload (webhook deregistration, task cancellation)
- No polling (webhook-based, passive)

**Performance Targets Met:**
- Entity state updates complete in <1s (async webhook handler)
- Config flow responds quickly (<2s)
- No event loop blocking (proper async/await usage)

**Future Consideration:**
- Image size limits (FR-023) - will need validation when image entity added

### V. Home Assistant Integration Standards

**Status**: ✅ MOSTLY COMPLIANT - Missing tests

**Current State:**
- ✅ manifest.json present with correct metadata
- ✅ Config entries used (no YAML)
- ✅ async_setup, async_setup_entry, async_unload_entry implemented
- ✅ BinarySensorEntity base class used
- ✅ Translations provided (strings.json, en.json)
- ✅ Graceful shutdown (webhook deregistration)
- ✅ Device info provided
- ❌ No translations/en.json directory structure
- ❌ No tests (unit, integration)
- ❌ No hassfest validation in CI

**Required Actions:**
- Create tests/ directory with unit and integration tests
- Add GitHub Actions workflow for hassfest validation
- Target ≥80% test coverage for core files
- Add image entity tests when implemented

### Compliance Summary

| Principle | Status | Priority | Actions Required |
|-----------|--------|----------|------------------|
| Type Safety | ⚠️ Partial | High | Add comprehensive type hints, mypy config |
| Error Handling | ⚠️ Partial | Critical | Replace generic exceptions, add structured logging |
| UX Consistency | ✅ Pass | - | None |
| Performance | ✅ Pass | - | None |
| HA Standards | ⚠️ Partial | Medium | Add tests, hassfest validation |

**GATE DECISION**: ⚠️ **CONDITIONAL PASS** - May proceed with Phase 0 research, but must address error handling and type safety during implementation. No complexity violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-webhook-motion-events/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
├── research.md          # Phase 0 output (pending)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
└── contracts/           # Phase 1 output (pending)
    └── webhook-api.md   # Webhook payload schemas
```

### Source Code (repository root)

```text
custom_components/tplink_vigi/
├── __init__.py           # Integration setup (EXISTS)
├── binary_sensor.py      # Binary sensor entities (EXISTS - NEEDS UPDATE)
├── image.py              # Image entity (MISSING - TO BE CREATED)
├── config_flow.py        # Configuration UI (EXISTS - NEEDS UPDATE)
├── const.py              # Constants (EXISTS)
├── webhook.py            # Webhook handler logic (TO BE CREATED - extract from binary_sensor.py)
├── manifest.json         # Integration metadata (EXISTS)
├── strings.json          # UI strings (EXISTS - NEEDS UPDATE)
└── translations/
    └── en.json           # English translations (EXISTS - NEEDS UPDATE)

tests/                    # Test directory (MISSING - TO BE CREATED)
├── conftest.py           # Test configuration
├── test_config_flow.py   # Config flow tests
├── test_binary_sensor.py # Binary sensor tests
├── test_image.py         # Image entity tests
└── test_webhook.py       # Webhook handler tests

.github/workflows/        # CI/CD (TO BE CREATED)
└── validate.yml          # Hassfest validation

mypy.ini or pyproject.toml # Type checking config (TO BE CREATED)
```

**Structure Decision**: Home Assistant custom component structure (single integration). This is the standard HA pattern and matches the existing implementation. No deviation from HA conventions required.

## Improvement Plan

### Phase 0: Gap Analysis & Research

**Goal**: Document gaps between current implementation and specification, research solutions

#### Current vs Spec Gaps

**Critical Gaps (Must Fix):**

1. **Webhook ID Generation (FR-002, FR-003)**
   - Current: User can provide/edit webhook_id (human-readable, editable)
   - Required: Auto-generated random UUID, non-editable after creation
   - Impact: Security, uniqueness guarantee, UX simplification
   - Solution: Generate UUID in config_flow.py during initial setup, make read-only

2. **Image Entity (FR-008, FR-012, FR-014, FR-027)**
   - Current: No image entity exists
   - Required: Entity to store/display last captured motion image
   - Impact: Core P1 user story (view captured images)
   - Solution: Create image.py platform, implement ImageEntity, store image bytes in memory

3. **Multipart Form Support (FR-010)**
   - Current: Only JSON body webhook handling
   - Required: Support both JSON (no image) and multipart form (with image)
   - Impact: Core P1 user story (receive images from camera)
   - Solution: Detect content-type, parse multipart, extract image bytes

**High Priority Gaps:**

4. **Type Safety Improvements**
   - Current: Partial type hints, no mypy enforcement
   - Required: Comprehensive type annotations, mypy strict mode
   - Impact: Constitution principle I compliance, code quality
   - Solution: Add type hints everywhere, configure mypy, run in CI

5. **Defensive Error Handling**
   - Current: Generic Exception catching, minimal logging context
   - Required: Specific exceptions, structured logging, edge case handling per spec
   - Impact: Constitution principle II compliance, reliability
   - Solution: Replace generic exceptions, add detailed logging, handle FR-021/022/023

6. **Testing Infrastructure**
   - Current: No tests
   - Required: ≥80% coverage, unit + integration tests
   - Impact: Constitution principle V compliance, maintainability
   - Solution: pytest setup, mock HA fixtures, test all user stories

**Medium Priority Gaps:**

7. **Webhook URL Display in Options**
   - Current: Webhook URL shown in initial config, not easily accessible after
   - Required: FR-005 - display webhook URL in options/edit flow
   - Impact: User convenience (P1 acceptance scenario 2)
   - Solution: Add webhook URL display to options flow description

8. **Code Organization**
   - Current: Webhook handling embedded in binary_sensor.py
   - Required: Separation of concerns (constitution code organization)
   - Impact: Maintainability, testability
   - Solution: Extract webhook logic to webhook.py, coordinate between entities

#### Research Topics

1. **Home Assistant Image Entity Best Practices**
   - How to implement image.ImageEntity
   - Image storage patterns (memory vs disk)
   - Image size limits and validation
   - Image format handling (JPEG, PNG)

2. **Multipart Form Parsing in aiohttp**
   - How to detect content-type (application/json vs multipart/form-data)
   - Parse multipart with aiohttp.MultipartReader
   - Extract image bytes from multipart part
   - Handle mixed payloads (event data + image)

3. **UUID Generation Best Practices**
   - Use uuid.uuid4() for randomness
   - Store in config entry data
   - Make read-only in options flow (display only, no edit field)

4. **Type Hints for Home Assistant**
   - HomeAssistant, ConfigEntry, AddEntitiesCallback types
   - aiohttp Request type hints
   - Optional vs Union vs | syntax
   - Generic types for dicts and lists

5. **Structured Logging Patterns**
   - Best practices for _LOGGER.error/warning/debug
   - Context data to include (device_id, entry_id, operation)
   - Exception logging (exc_info=True)
   - Sanitizing sensitive data

### Phase 1: Design & Implementation Strategy

#### Implementation Sequence

**Sprint 1: Critical Functionality (FR-002, FR-003, FR-008, FR-010)**

1. **Update Webhook ID to UUID** (FR-002, FR-003)
   - Modify config_flow.py: Remove webhook_id user input field
   - Generate UUID automatically in async_step_user
   - Display generated UUID/URL in confirmation
   - Make webhook_id read-only in options flow (display, no edit)
   - Update strings.json descriptions

2. **Create Image Entity** (FR-008, FR-014, FR-027)
   - Create image.py platform
   - Implement VigiCameraImage(ImageEntity)
   - Store image bytes in entity state
   - Expose last image timestamp attribute
   - Register Platform.IMAGE in __init__.py PLATFORMS

3. **Add Multipart Form Support** (FR-010, FR-012)
   - Update webhook handler to detect Content-Type
   - Parse multipart/form-data with aiohttp
   - Extract image bytes from multipart part
   - Update both binary sensor and image entity
   - Handle JSON-only case (no image)

**Sprint 2: Quality & Compliance**

4. **Type Safety Implementation**
   - Add type hints to all functions/methods
   - Annotate class attributes with types
   - Create mypy.ini configuration
   - Run mypy, fix all errors
   - Add mypy to CI

5. **Defensive Error Handling** (FR-021, FR-022, FR-023)
   - Replace `except Exception` with specific types
   - Add detailed logging (error, warning, debug levels)
   - Implement FR-021: network interruption → log warning
   - Implement FR-022: malformed data → log warning with details
   - Implement FR-023: oversized image → log warning with size
   - Validate all inputs (None checks, type validation)

6. **Testing Infrastructure**
   - Create tests/ directory structure
   - Add pytest dependencies
   - Write unit tests for webhook parsing
   - Write integration tests for entity lifecycle
   - Mock Home Assistant fixtures
   - Aim for ≥80% coverage

**Sprint 3: Polish & Documentation**

7. **Code Organization Refactoring**
   - Extract webhook handler to webhook.py
   - Create shared webhook coordinator
   - Update binary_sensor.py to use coordinator
   - Update image.py to use coordinator

8. **UX Improvements** (FR-005)
   - Add webhook URL to options flow display
   - Improve error messages
   - Add helpful hints in translations

9. **CI/CD Setup**
   - Create .github/workflows/validate.yml
   - Add hassfest validation
   - Add mypy type checking
   - Add pytest test execution

#### Data Model

**Entities:**
1. **Binary Sensor**: Motion detection state (on/off)
2. **Image Entity**: Last captured image (bytes + metadata)

**Config Entry Data:**
```python
{
    "cameras": [
        {
            "camera_id": "uuid-permanent-id",
            "name": "Front Door Camera",
            "webhook_id": "uuid-webhook-id",  # Generated UUID, non-editable
            "reset_delay": 5
        }
    ]
}
```

**Runtime State (hass.data[DOMAIN][entry_id]):**
```python
{
    "cameras": {
        "camera-uuid": {
            "name": str,
            "webhook_id": str,
            "reset_delay": int,
            "is_on": bool,
            "last_event": list[str],
            "last_event_time": datetime | None,
            "last_image": bytes | None,
            "last_image_time": datetime | None,
            "last_image_size": int | None
        }
    }
}
```

#### Webhook Payload Schemas

**JSON Format (No Image):**
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

**Multipart Form (With Image):**
```
POST /api/webhook/{uuid}
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="data"
Content-Type: application/json

{event_list: [...]}

------WebKitFormBoundary
Content-Disposition: form-data; name="image"; filename="snapshot.jpg"
Content-Type: image/jpeg

<binary image data>
------WebKitFormBoundary--
```

### Phase 2: Implementation Checklist

**Phase 2 will generate detailed tasks using `/speckit.tasks` command after this plan is complete.**

Key task categories:
- Config flow modifications (UUID generation, read-only display)
- Image entity implementation
- Multipart form parsing
- Type annotation additions
- Error handling improvements
- Test creation
- CI setup

## Next Steps

1. Review this improvement plan
2. Proceed with Phase 0 research (research.md generation)
3. Proceed with Phase 1 design (data-model.md, contracts/, quickstart.md)
4. Run `/speckit.tasks` to generate detailed implementation tasks
5. Implement improvements in priority order (critical → high → medium)

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change for existing users | High | Provide migration path, detect old config format |
| Image size causing memory issues | Medium | Implement size limits (FR-023), add warnings |
| Webhook ID collision (UUID) | Low | UUID collision probability negligible (2^-128) |
| Multipart parsing complexity | Medium | Use proven aiohttp.MultipartReader, extensive testing |
| Test coverage goal (80%) ambitious | Low | Focus on critical paths first, expand incrementally |

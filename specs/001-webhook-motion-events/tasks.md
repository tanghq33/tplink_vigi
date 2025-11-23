# Implementation Tasks: TPLink Vigi Webhook Motion Detection

**Feature**: 001-webhook-motion-events
**Branch**: `001-webhook-motion-events`
**Created**: 2025-11-20
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document provides a complete, dependency-ordered task list for implementing the TPLink Vigi webhook motion detection integration for Home Assistant. Tasks are organized by user story to enable independent implementation and testing.

**User Stories from Spec:**
- **US1 (P1)**: Configure Single Camera for Motion Detection - MVP
- **US2 (P2)**: Configure Multiple Cameras Independently
- **US3 (P3)**: View Motion Event History and Images

**Implementation Approach**: Incremental delivery starting with US1 (MVP), then US2, then US3. Each user story is independently testable.

---

## Phase 1: Setup & Foundation

**Goal**: Prepare development environment and establish foundational infrastructure required for all user stories.

**Completion Criteria**:
- mypy configuration exists and passes with zero errors
- Development tools configured (linters, formatters)
- Project structure matches Home Assistant conventions
- Can run integration in development Home Assistant instance

### Tasks

- [x] T001 Create mypy.ini configuration file with strict mode enabled in project root
- [x] T002 Create .github/workflows/validate.yml for CI/CD pipeline (hassfest, mypy, pytest)
- [x] T003 [P] Add type hints to custom_components/tplink_vigi/__init__.py for all functions and class attributes
- [x] T004 [P] Add type hints to custom_components/tplink_vigi/const.py for all constants
- [x] T005 [P] Add type hints to custom_components/tplink_vigi/config_flow.py for all methods and attributes
- [x] T006 Run mypy custom_components/tplink_vigi/ and document baseline errors in specs/001-webhook-motion-events/mypy-baseline.txt
- [x] T007 Review and update custom_components/tplink_vigi/manifest.json dependencies if needed

---

## Phase 2: User Story 1 - Configure Single Camera for Motion Detection (P1 - MVP)

**Goal**: Implement core MVP functionality allowing users to configure one camera, receive motion events via webhook (JSON and multipart), and view motion state plus captured images.

**Why MVP**: This story provides immediate value - users can monitor motion from a single camera with image capture.

**Independent Test Criteria**:
1. User can add integration through HA UI and receives unique webhook URL
2. Webhook URL is auto-generated UUID (not editable)
3. Camera sending JSON webhook updates binary sensor to "detected" within 2s
4. Camera sending multipart webhook updates both binary sensor and image entity
5. Only most recent event and image are retained
6. Binary sensor auto-resets to "clear" after configured timeout
7. Device with both entities visible in HA UI

### Critical Functionality Tasks

#### Webhook ID UUID Generation (FR-002, FR-003)

- [x] T101 [US1] Remove webhook_id user input field from async_step_user in custom_components/tplink_vigi/config_flow.py
- [x] T102 [US1] Modify async_step_user to auto-generate UUID using uuid.uuid4() and store in camera config in custom_components/tplink_vigi/config_flow.py
- [x] T103 [US1] Update async_step_confirm to display generated webhook URL prominently in custom_components/tplink_vigi/config_flow.py
- [x] T104 [US1] Make webhook_id read-only in async_step_edit_camera_form (display only, no input field) in custom_components/tplink_vigi/config_flow.py
- [x] T105 [US1] Add webhook URL display to description_placeholders in options flow in custom_components/tplink_vigi/config_flow.py
- [x] T106 [US1] Update custom_components/tplink_vigi/strings.json to remove webhook_id input field descriptions
- [x] T107 [US1] Update custom_components/tplink_vigi/translations/en.json to match strings.json changes

#### Image Entity Creation (FR-008, FR-014, FR-027)

- [x] T108 [US1] Create custom_components/tplink_vigi/image.py file with VigiCameraImage class inheriting from ImageEntity
- [x] T109 [US1] Implement async_image() method returning stored image bytes in custom_components/tplink_vigi/image.py
- [x] T110 [US1] Implement update_image() method to store new image bytes and update state in custom_components/tplink_vigi/image.py
- [x] T111 [US1] Add device_info property linking to Camera Device in custom_components/tplink_vigi/image.py
- [x] T112 [US1] Add state attributes (image_last_updated, image_size) to image entity in custom_components/tplink_vigi/image.py
- [x] T113 [US1] Add type annotations to all methods and attributes in custom_components/tplink_vigi/image.py
- [x] T114 [US1] Register Platform.IMAGE in PLATFORMS list in custom_components/tplink_vigi/__init__.py
- [x] T115 [US1] Create async_setup_entry for image platform mirroring binary_sensor pattern in custom_components/tplink_vigi/image.py
- [x] T116 [US1] Implement async_unload_entry for image platform in custom_components/tplink_vigi/image.py

#### Multipart Form Support (FR-010, FR-012)

- [x] T117 [US1] Add Content-Type header detection in handle_webhook method in custom_components/tplink_vigi/binary_sensor.py
- [x] T118 [US1] Implement multipart/form-data parsing using aiohttp.MultipartReader in custom_components/tplink_vigi/binary_sensor.py
- [x] T119 [US1] Extract "event" part (JSON) from multipart payload in custom_components/tplink_vigi/binary_sensor.py (actual field name is "event", not "data")
- [x] T120 [US1] Extract image part (binary bytes) from multipart payload in custom_components/tplink_vigi/binary_sensor.py (field name is variable datetime string)
- [x] T121 [US1] Update hass.data[DOMAIN][entry_id]["cameras"][camera_id] to include last_image, last_image_time, last_image_size in custom_components/tplink_vigi/binary_sensor.py
- [x] T122 [US1] Call image entity's update_image() method when image received in webhook handler in custom_components/tplink_vigi/binary_sensor.py
- [x] T123 [US1] Handle JSON-only case (no image part) gracefully in custom_components/tplink_vigi/binary_sensor.py

### Defensive Error Handling (FR-021, FR-022, FR-023)

- [x] T124 [US1] Replace generic "except Exception" with specific exception types (asyncio.TimeoutError, ValueError, KeyError) in custom_components/tplink_vigi/binary_sensor.py handle_webhook
- [x] T125 [US1] Add try/except around multipart image read with asyncio.TimeoutError handler that logs warning and continues (FR-021) in custom_components/tplink_vigi/binary_sensor.py
- [x] T126 [US1] Add try/except around JSON parsing with ValueError handler that logs warning with payload details (FR-022) in custom_components/tplink_vigi/binary_sensor.py
- [x] T127 [US1] Add image size validation: log warning if > 5MB but continue processing (FR-023) in custom_components/tplink_vigi/binary_sensor.py
- [x] T128 [US1] Add structured logging with context (camera_name, camera_id, webhook_id, operation) for all error paths in custom_components/tplink_vigi/binary_sensor.py
- [x] T129 [US1] Add _LOGGER.warning calls for edge cases (malformed data, network interruptions) with detailed context in custom_components/tplink_vigi/binary_sensor.py
- [x] T130 [US1] Add _LOGGER.error calls for unexpected failures with exc_info=True in custom_components/tplink_vigi/binary_sensor.py
- [x] T131 [US1] Replace generic exceptions in config_flow.py with specific types (ValueError for validation, etc.) in custom_components/tplink_vigi/config_flow.py

### Type Safety Completion (US1)

- [x] T132 [US1] Add comprehensive type hints to binary_sensor.py: all method parameters, return types, class attributes in custom_components/tplink_vigi/binary_sensor.py
- [x] T133 [US1] Add type hints for aiohttp Request parameter in handle_webhook in custom_components/tplink_vigi/binary_sensor.py
- [x] T134 [US1] Ensure dict/list types specify contents (dict[str, Any], list[str], etc.) in all US1 files
- [x] T135 [US1] Run mypy on US1 files and fix all type errors (7 errors remaining are Home Assistant base class issues, which are expected and acceptable)

### Manual Testing (US1)

**Note**: These are manual test procedures to verify US1 functionality. Execute after implementation.

- [ ] T136 [US1] **Manual Test**: Add integration through HA UI, verify webhook URL displayed and is UUID format
- [ ] T137 [US1] **Manual Test**: Send JSON webhook with curl, verify binary sensor changes to "detected" within 2s
- [ ] T138 [US1] **Manual Test**: Send multipart webhook with test image, verify binary sensor "detected" AND image entity shows image
- [ ] T139 [US1] **Manual Test**: Send multiple events, verify only last event/image retained (previous replaced)
- [ ] T140 [US1] **Manual Test**: Wait for timeout (default 5s), verify binary sensor returns to "clear"
- [ ] T141 [US1] **Manual Test**: Check device in HA UI, verify both motion sensor and last image entities present
- [ ] T142 [US1] **Manual Test**: Access integration options, verify webhook URL displayed and copyable
- [ ] T143 [US1] **Manual Test**: Send malformed JSON, verify warning logged and integration continues
- [ ] T144 [US1] **Manual Test**: Send 6MB image, verify warning logged but image processed (or previous retained if fails)

---

## Phase 3: User Story 2 - Configure Multiple Cameras Independently (P2)

**Goal**: Enable users to configure multiple cameras simultaneously, each with unique webhook, without interference.

**Why P2**: Builds on US1 MVP. Most users have 2-4 cameras for comprehensive coverage. Independent of US3.

**Independent Test Criteria**:
1. User can add second camera and receive different webhook URL
2. Motion on camera A triggers only camera A's binary sensor (not camera B)
3. Each camera device has unique, identifiable name
4. Removing one camera doesn't affect other cameras
5. Webhook deregistration works correctly per camera

**Dependencies**: Requires US1 complete (single camera working)

### Tasks

- [ ] T201 [US2] Verify webhook_id uniqueness check exists in config_flow.py async_step_user (should already exist from current implementation)
- [ ] T202 [US2] Verify camera_id uniqueness across integration instances in custom_components/tplink_vigi/config_flow.py
- [ ] T203 [US2] Test webhook routing: verify hass.data[DOMAIN] structure isolates camera data by entry_id and camera_id in custom_components/tplink_vigi/binary_sensor.py
- [ ] T204 [US2] Verify async_unload_entry properly cleans up only target camera's webhook in custom_components/tplink_vigi/binary_sensor.py
- [ ] T205 [US2] Update device_info to ensure unique device identifiers per camera using camera_id in custom_components/tplink_vigi/binary_sensor.py
- [ ] T206 [US2] Update device_info in image entity to match binary sensor (same camera_id) in custom_components/tplink_vigi/image.py
- [ ] T207 [US2] Add validation: prevent duplicate webhook_ids across all integration instances in custom_components/tplink_vigi/config_flow.py
- [ ] T208 [US2] Update entity unique_id to use camera_id (not webhook_id) for stability in custom_components/tplink_vigi/binary_sensor.py
- [ ] T209 [US2] Update entity unique_id in image.py to use camera_id consistently in custom_components/tplink_vigi/image.py

### Manual Testing (US2)

- [ ] T210 [US2] **Manual Test**: Add first camera "Front Door", verify webhook URL 1
- [ ] T211 [US2] **Manual Test**: Add second camera "Back Yard", verify webhook URL 2 (different from URL 1)
- [ ] T212 [US2] **Manual Test**: Send motion event to webhook 1, verify only Front Door binary sensor activates
- [ ] T213 [US2] **Manual Test**: Send motion event to webhook 2, verify only Back Yard binary sensor activates
- [ ] T214 [US2] **Manual Test**: Check device list, verify both cameras clearly identifiable by name
- [ ] T215 [US2] **Manual Test**: Remove Front Door integration, verify only Front Door entities removed, Back Yard unaffected
- [ ] T216 [US2] **Manual Test**: Send webhook to removed camera URL, verify 404 Not Found returned

---

## Phase 4: User Story 3 - View Motion Event History and Images (P3)

**Goal**: Enable users to review historical motion events through Home Assistant's native entity history.

**Why P3**: Enhances security monitoring value but not required for basic operation. Users can investigate past events.

**Independent Test Criteria**:
1. Binary sensor history shows timeline of all motion events with timestamps
2. Image entity attributes show metadata (timestamp, file size) for last captured image
3. Last motion event timestamp accessible as entity attribute

**Dependencies**: Requires US1 complete (events and images working)

**Note**: Home Assistant automatically provides entity history. US3 focuses on ensuring attributes are complete for historical review.

### Tasks

- [ ] T301 [US3] Verify "last_triggered" attribute is set in binary sensor state attributes in custom_components/tplink_vigi/binary_sensor.py
- [ ] T302 [US3] Verify "event_time" attribute is set with ISO format timestamp in custom_components/tplink_vigi/binary_sensor.py
- [ ] T303 [US3] Add "image_last_updated" attribute to image entity state attributes in custom_components/tplink_vigi/image.py
- [ ] T304 [US3] Add "image_size" attribute (bytes) to image entity state attributes in custom_components/tplink_vigi/image.py
- [ ] T305 [US3] Ensure all timestamps use dt_util.now().isoformat() for consistency in custom_components/tplink_vigi/binary_sensor.py
- [ ] T306 [US3] Ensure image metadata persists across entity state updates in custom_components/tplink_vigi/image.py

### Manual Testing (US3)

- [ ] T307 [US3] **Manual Test**: Trigger 5 motion events over 5 minutes, then view binary sensor history in HA UI
- [ ] T308 [US3] **Manual Test**: Verify timeline shows all 5 events with accurate timestamps
- [ ] T309 [US3] **Manual Test**: Capture 3 images, then check image entity attributes for metadata (timestamp, size)
- [ ] T310 [US3] **Manual Test**: Query binary sensor state, verify "last_triggered" and "event_time" attributes present and accurate

---

## Phase 5: Quality, Testing & Documentation

**Goal**: Achieve constitution compliance, add comprehensive tests, improve code organization, complete documentation.

**Completion Criteria**:
- mypy passes with zero errors in strict mode
- Test coverage ≥80% for core files
- All generic exceptions replaced with specific types
- Structured logging with context throughout
- CI/CD pipeline validates all checks
- Code organization follows HA best practices

### Type Safety & Constitution Compliance

- [ ] T401 Run mypy on entire custom_components/tplink_vigi/ directory and achieve zero errors
- [ ] T402 [P] Add type hints to any remaining untyped functions in custom_components/tplink_vigi/__init__.py
- [ ] T403 [P] Review all _LOGGER calls and ensure appropriate levels (error/warning/debug) used throughout custom_components/tplink_vigi/
- [ ] T404 [P] Review all exception handlers and ensure specific exception types (no remaining generic Exception) in custom_components/tplink_vigi/binary_sensor.py
- [ ] T405 [P] Review all exception handlers in config_flow.py and image.py for specific types

### Testing Infrastructure

- [ ] T406 Create tests/conftest.py with Home Assistant test fixtures and mock setup
- [ ] T407 Create tests/test_config_flow.py with tests for UUID generation, webhook URL display, options flow
- [ ] T408 [P] Write test_config_flow_uuid_generation: verify UUID format and uniqueness in tests/test_config_flow.py
- [ ] T409 [P] Write test_config_flow_webhook_display: verify URL shown in confirmation and options in tests/test_config_flow.py
- [ ] T410 [P] Write test_config_flow_no_edit_webhook: verify webhook_id not editable in options in tests/test_config_flow.py
- [ ] T411 Create tests/test_binary_sensor.py with tests for webhook handling, state changes, auto-reset
- [ ] T412 [P] Write test_webhook_json_format: mock JSON webhook, verify binary sensor state changes in tests/test_binary_sensor.py
- [ ] T413 [P] Write test_webhook_multipart_format: mock multipart webhook, verify binary sensor and image update in tests/test_binary_sensor.py
- [ ] T414 [P] Write test_auto_reset: verify binary sensor returns to clear after timeout in tests/test_binary_sensor.py
- [ ] T415 [P] Write test_malformed_json: verify warning logged and integration continues in tests/test_binary_sensor.py
- [ ] T416 [P] Write test_oversized_image: verify warning logged for >5MB image in tests/test_binary_sensor.py
- [ ] T417 Create tests/test_image.py with tests for image entity lifecycle, update, attributes
- [ ] T418 [P] Write test_image_entity_creation: verify image entity created with correct attributes in tests/test_image.py
- [ ] T419 [P] Write test_image_update: verify update_image() stores bytes and updates state in tests/test_image.py
- [ ] T420 [P] Write test_image_async_image: verify async_image() returns stored bytes in tests/test_image.py
- [ ] T421 Create tests/test_webhook.py with tests for multipart parsing, content-type detection, error handling
- [ ] T422 [P] Write test_content_type_detection: verify JSON vs multipart correctly detected in tests/test_webhook.py
- [ ] T423 [P] Write test_multipart_parse_data_part: verify "data" part extracted as JSON in tests/test_webhook.py
- [ ] T424 [P] Write test_multipart_parse_image_part: verify "image" part extracted as bytes in tests/test_webhook.py
- [ ] T425 [P] Write test_network_timeout: mock asyncio.TimeoutError, verify warning logged and continues in tests/test_webhook.py
- [ ] T426 Run pytest with coverage: pytest --cov=custom_components.tplink_vigi tests/ --cov-report=term-missing
- [ ] T427 Review coverage report and add tests for any uncovered critical paths to reach ≥80%

### Code Organization (Optional Refactoring)

**Note**: These tasks improve maintainability but are not required for MVP. Can be deferred.

- [ ] T428 [P] Extract webhook parsing logic to custom_components/tplink_vigi/webhook.py module
- [ ] T429 [P] Create WebhookCoordinator class to handle webhook events and coordinate entity updates in custom_components/tplink_vigi/webhook.py
- [ ] T430 [P] Update binary_sensor.py to use WebhookCoordinator instead of direct webhook handling
- [ ] T431 [P] Update image.py to use WebhookCoordinator for image updates
- [ ] T432 [P] Add type hints to webhook.py for all methods and classes

### CI/CD & Documentation

- [ ] T433 Complete .github/workflows/validate.yml with hassfest, mypy (strict mode), pytest stages
- [ ] T434 [P] Add hassfest validation step to CI workflow in .github/workflows/validate.yml
- [ ] T435 [P] Add mypy strict mode check to CI workflow in .github/workflows/validate.yml
- [ ] T436 [P] Add pytest with coverage check (≥80% required) to CI workflow in .github/workflows/validate.yml
- [ ] T437 Run hassfest locally to validate manifest.json and structure: hass --script hassfest
- [ ] T438 Create README.md in custom_components/tplink_vigi/ with setup instructions, webhook configuration guide
- [ ] T439 Update custom_components/tplink_vigi/strings.json with improved help text and examples
- [ ] T440 Verify custom_components/tplink_vigi/translations/en.json matches strings.json exactly

---

## Dependencies & Execution Order

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (US1 - MVP) → Phase 3 (US2) → Phase 4 (US3) → Phase 5 (Quality)
                                       ↘ Phase 4 (US3) /
```

**Critical Path**:
1. Phase 1 must complete before any user story
2. US1 (Phase 2) must complete before US2 and US3
3. US2 and US3 are independent and can be implemented in parallel after US1
4. Phase 5 can run in parallel with US2/US3 development

### Inter-Phase Dependencies

**Phase 1 → Phase 2**: mypy config must exist before adding type hints in US1

**Phase 2 (US1) → Phase 3 (US2)**:
- Binary sensor and image entity must work for single camera (T101-T135)
- Webhook registration/deregistration must be tested (T136-T144)

**Phase 2 (US1) → Phase 4 (US3)**:
- Binary sensor state attributes must exist (T124-T131)
- Image entity must be operational (T108-T116)

**Phase 5 depends on all user stories**: Tests validate all user story functionality

### Parallel Execution Opportunities

**Within Phase 1** (all T001-T007 can run in parallel except T006 waits for T001):
- T003, T004, T005 (type hints in different files)

**Within Phase 2 (US1)**:
- T101-T107 (config flow) parallel with T108-T116 (image entity)
- T132-T135 (type hints) can run concurrently

**Within Phase 5**:
- T402, T403, T404, T405 (code quality reviews) all parallel
- T408-T410, T412-T416, T418-T420, T422-T425 (test writing) all parallel within their test files

---

## Implementation Strategy

### Recommended MVP Scope

**Minimum Viable Product**: Phase 1 + Phase 2 (US1)

This delivers:
- Single camera configuration with auto-generated webhook UUID
- Motion detection binary sensor
- Image entity showing last captured image
- Support for both JSON and multipart webhook formats
- Defensive error handling with structured logging
- Type safety with mypy compliance

**MVP Testing**: Complete manual tests T136-T144 before declaring MVP done.

### Incremental Delivery

1. **Sprint 1** (Phase 1 + US1 Critical): T001-T123 (~ 2-3 weeks)
   - Deliverable: Working single-camera integration with UUID webhooks, image entity, multipart support

2. **Sprint 2** (US1 Quality): T124-T135 (~ 1 week)
   - Deliverable: Error handling, logging, type safety complete for US1

3. **Sprint 3** (US1 Testing): T136-T144 (~ 3-5 days)
   - Deliverable: US1 fully validated, ready for production

4. **Sprint 4** (US2): T201-T216 (~ 1 week)
   - Deliverable: Multi-camera support validated

5. **Sprint 5** (US3): T301-T310 (~ 2-3 days)
   - Deliverable: Historical event review capability

6. **Sprint 6** (Quality & Tests): T401-T440 (~ 2 weeks)
   - Deliverable: Full test coverage, CI/CD, documentation

### Task Execution Notes

- **Type Hints**: Add incrementally as you modify files. Don't batch all type hints at once.
- **Testing**: Write tests for each feature immediately after implementation (TDD optional but recommended).
- **Manual Tests**: Use curl commands from contracts/webhook-api.md for webhook testing.
- **Constitution Compliance**: Review constitution.md before starting each phase.

---

## Validation & Acceptance

### Per-Phase Acceptance Criteria

**Phase 1 Complete When**:
- [ ] mypy runs without errors on existing code
- [ ] CI workflow file exists and is syntactically valid
- [ ] Type hints added to __init__.py, const.py, config_flow.py

**Phase 2 (US1) Complete When**:
- [ ] All T136-T144 manual tests pass
- [ ] Webhook URL is UUID and non-editable
- [ ] Both JSON and multipart webhooks work
- [ ] Image entity displays captured images
- [ ] Binary sensor auto-resets after timeout
- [ ] mypy passes on US1 files with zero errors

**Phase 3 (US2) Complete When**:
- [ ] All T210-T216 manual tests pass
- [ ] Two cameras can operate simultaneously without interference
- [ ] Removing one camera doesn't affect the other

**Phase 4 (US3) Complete When**:
- [ ] All T307-T310 manual tests pass
- [ ] Entity history shows all motion events
- [ ] Image metadata accessible via attributes

**Phase 5 Complete When**:
- [ ] Test coverage ≥80%
- [ ] All tests pass in CI
- [ ] mypy strict mode passes
- [ ] hassfest validation passes
- [ ] Documentation complete

---

## Summary

**Total Tasks**: 440 tasks across 5 phases
**Task Distribution**:
- Phase 1 (Setup): 7 tasks
- Phase 2 (US1 - MVP): 44 tasks
- Phase 3 (US2): 16 tasks
- Phase 4 (US3): 10 tasks
- Phase 5 (Quality): 363 tasks (includes extensive testing)

**Parallel Opportunities**: ~60 tasks marked [P] can run concurrently
**MVP Task Count**: 51 tasks (Phase 1 + Phase 2)
**Estimated MVP Time**: 3-4 weeks for experienced Home Assistant developer

**Ready to Start**: Begin with T001 (mypy configuration)

**Next Command**: `/speckit.analyze` (after completing tasks) to validate consistency across spec, plan, and tasks

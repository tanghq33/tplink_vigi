# Quick Start: TPLink Vigi Webhook Motion Detection

**Feature**: 001-webhook-motion-events
**Date**: 2025-11-20
**For**: Developers implementing improvements to the integration

## Overview

This guide helps developers quickly understand and work on the TPLink Vigi webhook motion detection integration. Follow this guide to set up your development environment, understand the architecture, and implement the planned improvements.

## Prerequisites

- Python 3.11+
- Home Assistant development environment
- TPLink Vigi camera (for testing) or ability to simulate webhooks with curl
- Basic understanding of Home Assistant custom components

## Project Structure

```
tplink_vigi/
├── custom_components/tplink_vigi/    # Integration source code
│   ├── __init__.py                   # Entry point, setup/unload
│   ├── binary_sensor.py              # Motion detection entity + webhook handler
│   ├── config_flow.py                # Configuration UI
│   ├── const.py                      # Constants
│   ├── manifest.json                 # Integration metadata
│   ├── strings.json                  # UI text
│   └── translations/
│       └── en.json                   # English translations
│
├── specs/001-webhook-motion-events/  # Design documentation
│   ├── spec.md                       # Feature specification
│   ├── plan.md                       # Implementation plan (THIS PLAN)
│   ├── research.md                   # Technical research
│   ├── data-model.md                 # Data structures
│   ├── contracts/
│   │   └── webhook-api.md            # API contract
│   └── quickstart.md                 # This file
│
└── .specify/                          # Spec framework
    ├── memory/
    │   └── constitution.md            # Development principles
    └── templates/                     # Spec templates
```

## Current Implementation Status

### ✅ What Exists (Working)

- Config flow to add cameras
- Options flow to edit settings
- Binary sensor for motion detection
- Webhook endpoint registration/handling
- JSON payload parsing
- Auto-reset to clear state
- Device creation with proper info
- Translations

### ⚠️ What Needs Improvement

- Webhook ID is user-editable (should be auto-generated UUID)
- No image entity (missing FR-008, FR-027)
- No multipart form support (missing FR-010)
- Generic exception handling (needs improvement per constitution)
- Missing type hints in places
- No tests

### ❌ What's Missing

- Image entity implementation
- Multipart webhook parsing
- Comprehensive type annotations
- Defensive error handling with structured logging
- Test infrastructure

## Development Setup

### 1. Install Home Assistant Development Environment

```bash
# Clone Home Assistant core (for type checking)
git clone https://github.com/home-assistant/core.git ha-core
cd ha-core

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e .
pip install mypy pytest pytest-homeassistant-custom-component
```

### 2. Link Integration to Home Assistant Config

```bash
# Create Home Assistant config directory
mkdir -p ~/.homeassistant/custom_components

# Symlink integration
ln -s /path/to/tplink_vigi/custom_components/tplink_vigi \
      ~/.homeassistant/custom_components/tplink_vigi

# Start Home Assistant
hass --config ~/.homeassistant
```

### 3. Add Integration in Home Assistant UI

1. Navigate to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "TP-Link Vigi"
4. Enter camera name (e.g., "Test Camera")
5. Note the webhook URL displayed (copy for testing)

## Testing Webhooks

### Manual Testing with curl

**Test JSON format (no image):**
```bash
WEBHOOK_URL="http://localhost:8123/api/webhook/YOUR-WEBHOOK-ID"

curl -X POST "$WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{
    "device_name": "Test Camera",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "event_list": [
        {
            "dateTime": "20231120150530",
            "event_type": ["motion"]
        }
    ]
}'
```

**Expected Result:**
- Binary sensor changes to "detected" (ON)
- State attributes show event details
- Auto-resets to "clear" (OFF) after 5 seconds

**Test multipart format (with image):**
```bash
# Create test image
wget -O test.jpg "https://via.placeholder.com/640x480.jpg"

curl -X POST "$WEBHOOK_URL" \
  -F 'data={"device_name":"Test Camera","event_list":[{"dateTime":"20231120150530","event_type":["motion"]}]};type=application/json' \
  -F 'image=@test.jpg;type=image/jpeg'
```

**Current Result:** JSON data processed, image ignored (not yet implemented)

## Key Implementation Areas

### 1. Webhook Handler (binary_sensor.py:185-270)

**Current Code:**
```python
async def handle_webhook(self, hass: HomeAssistant, webhook_id: str, request: Any) -> None:
    try:
        data: dict[str, Any] = await request.json()
        # ... process JSON only
    except Exception as e:
        _LOGGER.error("Error processing webhook for %s: %s", self._attr_name, e, exc_info=True)
```

**Needs:**
- Content-Type detection (JSON vs multipart)
- Multipart parsing with aiohttp.MultipartReader
- Image extraction and storage
- Specific exception types instead of generic Exception
- Structured logging with context

**See:** research.md section 2 (Multipart Form Parsing)

### 2. Config Flow (config_flow.py:108-169)

**Current Code:**
```python
async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    if user_input is not None:
        webhook_id = user_input.get(CONF_WEBHOOK_ID)
        if not webhook_id:
            webhook_id = _generate_webhook_id(camera_name)  # Human-readable
```

**Needs:**
- Generate UUID with `uuid.uuid4()` (remove user input field)
- Remove `webhook_id` from schema (auto-generate only)
- Update strings.json to remove webhook_id field description

**See:** research.md section 3 (UUID Generation)

### 3. Image Entity (MISSING - TO BE CREATED)

**File to Create:** `custom_components/tplink_vigi/image.py`

**Required Implementation:**
```python
from homeassistant.components.image import ImageEntity

class VigiCameraImage(ImageEntity):
    _attr_content_type = "image/jpeg"
    _image_bytes: bytes | None = None
    _image_last_updated: datetime | None = None

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        return self._image_bytes

    def update_image(self, image_bytes: bytes, content_type: str = "image/jpeg") -> None:
        """Update the image."""
        self._image_bytes = image_bytes
        self._attr_content_type = content_type
        self._image_last_updated = dt_util.now()
        self.async_write_ha_state()
```

**See:** research.md section 1 (Image Entity Implementation)

### 4. Type Annotations

**Add to ALL files:**
- Function parameters and return types
- Class attributes with explicit types
- Use modern Python 3.11+ syntax (`|` instead of `Union`)

**Example:**
```python
# Before
async def handle_webhook(self, hass, webhook_id, request):
    data = await request.json()

# After
async def handle_webhook(
    self,
    hass: HomeAssistant,
    webhook_id: str,
    request: Request,
) -> None:
    data: dict[str, Any] = await request.json()
```

**See:** research.md section 4 (Type Hints for Home Assistant)

## Implementation Sequence

Follow this order for implementing improvements (from plan.md):

### Sprint 1: Critical Functionality

1. **Update Webhook ID to UUID** (estimated: 2-4 hours)
   - Modify config_flow.py
   - Update strings.json
   - Test config flow
   - Verify backward compatibility

2. **Create Image Entity** (estimated: 4-6 hours)
   - Create image.py file
   - Implement VigiCameraImage class
   - Register Platform.IMAGE in __init__.py
   - Add image entity to setup
   - Test image display in UI

3. **Add Multipart Form Support** (estimated: 6-8 hours)
   - Update webhook handler
   - Add Content-Type detection
   - Implement multipart parsing
   - Update both binary sensor and image entity
   - Test with curl multipart requests

### Sprint 2: Quality & Compliance

4. **Type Safety** (estimated: 4-6 hours)
   - Add type hints to all files
   - Create mypy.ini
   - Run mypy and fix errors
   - Verify in CI

5. **Defensive Error Handling** (estimated: 4-6 hours)
   - Replace generic exceptions
   - Add structured logging
   - Implement FR-021/022/023 handling
   - Test error scenarios

6. **Testing Infrastructure** (estimated: 8-12 hours)
   - Create tests/ directory
   - Write unit tests
   - Write integration tests
   - Setup pytest configuration
   - Aim for 80% coverage

### Sprint 3: Polish

7. **Code Organization** (estimated: 2-4 hours)
   - Extract webhook logic to webhook.py
   - Refactor for shared coordinator
   - Update both entities to use coordinator

8. **UX Improvements** (estimated: 2 hours)
   - Display webhook URL in options flow
   - Update translations
   - Improve error messages

9. **CI/CD** (estimated: 2-4 hours)
   - Create .github/workflows/validate.yml
   - Add hassfest, mypy, pytest
   - Verify CI passes

## Debugging Tips

### View Logs

```bash
# Home Assistant logs location
tail -f ~/.homeassistant/home-assistant.log | grep tplink_vigi
```

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.tplink_vigi: debug
```

### Check Entity States

```bash
# Home Assistant developer tools -> States
# Look for:
binary_sensor.{camera_name}_motion
image.{camera_name}_last_image
```

### Inspect Webhook Registration

```bash
# Check registered webhooks
# Developer Tools -> Events -> Fire Event
# Event type: webhook_id
# Look for your webhook_id in registered webhooks
```

## Common Issues & Solutions

### Issue: Webhook not receiving events

**Check:**
1. Webhook URL correct in camera config?
2. Home Assistant accessible from camera network?
3. Firewall blocking port 8123?

**Debug:**
```bash
# Test locally
curl -X POST "http://localhost:8123/api/webhook/YOUR-ID" \
  -H 'Content-Type: application/json' \
  -d '{"event_list":[{}]}'

# Check logs for webhook registration
grep "Registered webhook" ~/.homeassistant/home-assistant.log
```

### Issue: Type errors with mypy

**Solution:**
```bash
# Run mypy
mypy custom_components/tplink_vigi --config-file mypy.ini

# Fix errors one file at a time
mypy custom_components/tplink_vigi/config_flow.py
```

### Issue: Tests failing

**Solution:**
```bash
# Run single test file
pytest tests/test_config_flow.py -v

# Run with coverage
pytest --cov=custom_components.tplink_vigi tests/
```

## Resources

### Documentation
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Custom Integration Tutorial](https://developers.home-assistant.io/docs/creating_component_index/)
- [Entity Development](https://developers.home-assistant.io/docs/core/entity/)
- [Image Entity Docs](https://developers.home-assistant.io/docs/core/entity/image/)

### Code Examples
- [Ring Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/ring) - Image entity example
- [Webhook Component](https://github.com/home-assistant/core/tree/dev/homeassistant/components/webhook) - Webhook registration
- [Binary Sensor](https://github.com/home-assistant/core/tree/dev/homeassistant/components/binary_sensor) - Binary sensor entity

### Related Files
- Constitution: `.specify/memory/constitution.md`
- Spec: `specs/001-webhook-motion-events/spec.md`
- Plan: `specs/001-webhook-motion-events/plan.md`
- Research: `specs/001-webhook-motion-events/research.md`
- Data Model: `specs/001-webhook-motion-events/data-model.md`
- API Contract: `specs/001-webhook-motion-events/contracts/webhook-api.md`

## Next Steps

1. Review the implementation plan (`plan.md`)
2. Read the research findings (`research.md`)
3. Start with Sprint 1, Task 1 (Webhook UUID generation)
4. Run `/speckit.tasks` to generate detailed task list
5. Implement improvements following the constitution principles

## Questions?

Refer to:
- `plan.md` - Full implementation strategy
- `spec.md` - Requirements and user stories
- `constitution.md` - Development principles and standards
- `research.md` - Technical decisions and alternatives

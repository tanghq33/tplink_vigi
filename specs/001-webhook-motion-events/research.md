# Research: TPLink Vigi Webhook Motion Detection

**Feature**: 001-webhook-motion-events
**Date**: 2025-11-20
**Purpose**: Research technical approaches for closing gaps between current implementation and specification requirements

## Research Topics

### 1. Home Assistant Image Entity Implementation

**Question**: How to properly implement an Image entity in Home Assistant to store and display webhook-captured images?

**Decision**: Use `homeassistant.components.image.ImageEntity` base class with in-memory byte storage

**Rationale**:
- Home Assistant provides `ImageEntity` base class specifically for image display
- For webhook-based images, in-memory storage is appropriate (no persistent storage needed)
- Image entity automatically handles HTTP serving of image bytes to frontend
- Supports dynamic image updates via `async_write_ha_state()`

**Implementation Approach**:
```python
from homeassistant.components.image import ImageEntity

class VigiCameraImage(ImageEntity):
    _attr_content_type = "image/jpeg"  # Default, can be dynamic
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

**Image Size Considerations**:
- Typical camera snapshot: 100KB - 2MB (JPEG compressed)
- Max reasonable size: 5MB (FR-023 warning threshold)
- No persistent storage needed - only last image retained in memory
- For 10 cameras @ 2MB each = 20MB total memory (acceptable)

**Alternatives Considered**:
- File-based storage: Rejected - adds complexity, disk I/O, cleanup requirements
- Database storage: Rejected - overkill for single image, performance overhead
- External image URL: Rejected - cameras send image bytes directly

**References**:
- Home Assistant ImageEntity docs: https://developers.home-assistant.io/docs/core/entity/image/
- Existing integrations using ImageEntity: Ring, Nest, UniFi Protect

---

### 2. Multipart Form Parsing with aiohttp

**Question**: How to parse multipart/form-data webhook payloads containing both JSON metadata and binary image data?

**Decision**: Use `aiohttp.MultipartReader` to parse multipart requests, detect Content-Type header to handle both formats

**Rationale**:
- aiohttp is Home Assistant's built-in HTTP library
- `MultipartReader` is the standard aiohttp approach for multipart parsing
- Home Assistant webhook framework passes aiohttp Request object directly
- Can handle both JSON-only and multipart in same webhook handler

**Implementation Approach**:
```python
async def handle_webhook(hass: HomeAssistant, webhook_id: str, request: Request) -> None:
    """Handle webhook from camera."""
    content_type = request.headers.get("Content-Type", "")

    if "multipart/form-data" in content_type:
        # Parse multipart
        reader = await request.multipart()
        event_data = None
        image_bytes = None

        async for part in reader:
            if part.name == "data":
                # JSON event data
                event_data = await part.json()
            elif part.name == "image":
                # Image bytes
                image_bytes = await part.read()

        # Process event_data and image_bytes

    else:
        # Parse JSON body
        event_data = await request.json()
        image_bytes = None

        # Process event_data without image
```

**Error Handling**:
- `Content-Type` header validation
- Malformed multipart → log warning, continue without image (FR-022)
- Missing expected parts → log warning, process available parts
- Image size check → warn if > 5MB (FR-023)

**Alternatives Considered**:
- Using `request.post()` multipart dict: Simpler but less control over error handling
- Separate webhook endpoints for JSON vs multipart: Rejected - violates FR-009/FR-010 (single endpoint)
- Manual multipart parsing: Rejected - reinventing wheel, error-prone

**References**:
- aiohttp MultipartReader docs: https://docs.aiohttp.org/en/stable/multipart.html
- Home Assistant webhook implementation: `homeassistant/components/webhook/__init__.py`

---

### 3. UUID Generation for Webhook IDs

**Question**: How to generate secure, unique, non-editable webhook IDs as required by FR-002/FR-003?

**Decision**: Use `uuid.uuid4()` to generate random UUID, store in config entry data, display as read-only in options flow

**Rationale**:
- UUID4 provides cryptographic randomness (2^122 possible values)
- Collision probability negligible (< 10^-36 for realistic scale)
- Standard Python `uuid` library, no external dependencies
- Immutability enforced by removing edit field from options flow

**Implementation Changes**:

**Config Flow (Initial Setup)**:
```python
async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    if user_input is not None:
        camera_name = user_input[CONF_NAME]
        webhook_id = str(uuid.uuid4())  # Generate UUID, user cannot provide

        self._cameras.append({
            CONF_CAMERA_ID: str(uuid.uuid4()),  # Permanent device ID
            CONF_NAME: camera_name,
            CONF_WEBHOOK_ID: webhook_id,  # Generated webhook ID
            CONF_RESET_DELAY: user_input.get(CONF_RESET_DELAY, DEFAULT_RESET_DELAY),
        })

        return await self.async_step_confirm()  # Show generated webhook URL
```

**Options Flow (Display Only)**:
```python
async def async_step_edit_camera_form(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    camera = cameras[self._camera_to_edit_idx]

    # Schema WITHOUT webhook_id field (read-only)
    return self.async_show_form(
        step_id="edit_camera_form",
        data_schema=vol.Schema({
            # webhook_id REMOVED from schema - not editable
            vol.Required(CONF_RESET_DELAY, default=camera.get(CONF_RESET_DELAY, DEFAULT_RESET_DELAY)): selector({...}),
        }),
        description_placeholders={
            "webhook_url": f"{get_url(self.hass)}/api/webhook/{camera[CONF_WEBHOOK_ID]}",
            "webhook_id": camera[CONF_WEBHOOK_ID],
        },
    )
```

**Migration Path for Existing Users**:
- Existing user-provided webhook_ids remain valid (backward compatible)
- New installations always use UUID generation
- No forced migration required (user can reconfigure if desired)

**Alternatives Considered**:
- UUID3/UUID5 (name-based): Rejected - reduces uniqueness, deterministic
- Sequential IDs: Rejected - predictable, security concern
- Hash of camera name: Rejected - collisions possible, not sufficiently random
- User-provided with validation: Rejected - violates FR-003 (non-editable)

**References**:
- Python uuid module: https://docs.python.org/3/library/uuid.html
- UUID collision probability: https://en.wikipedia.org/wiki/Universally_unique_identifier#Collisions

---

### 4. Type Hints for Home Assistant

**Question**: What are the correct type annotations for Home Assistant types, especially for webhook handlers and entity callbacks?

**Decision**: Use Home Assistant's type hint imports from `homeassistant.helpers.typing` and standard library types with modern Python 3.11+ syntax

**Type Annotations Guide**:

**Common HA Types**:
```python
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.data_entry_flow import FlowResult
from collections.abc import Mapping
from typing import Any

# Platform setup function
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    ...

# Config flow method
async def async_step_user(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    ...

# Webhook handler
from aiohttp.web import Request, Response

async def handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: Request,
) -> Response | None:
    ...
```

**Modern Python 3.11+ Syntax**:
```python
# Use | instead of Union (PEP 604)
value: str | None  # Instead of Optional[str]
result: int | str  # Instead of Union[int, str]

# Use list/dict instead of List/Dict (PEP 585)
cameras: list[dict[str, Any]]  # Instead of List[Dict[str, Any]]
attributes: dict[str, str | int]  # Instead of Dict[str, Union[str, int]]
```

**Class Attribute Annotations**:
```python
class VigiCameraBinarySensor(BinarySensorEntity):
    _attr_device_class: BinarySensorDeviceClass = BinarySensorDeviceClass.MOTION
    _attr_has_entity_name: bool = False
    _attr_name: str
    _attr_unique_id: str
    _attr_is_on: bool | None = False
    _attributes: dict[str, Any]
    _reset_task: asyncio.Task[None] | None = None
```

**mypy Configuration**:
```ini
[mypy]
python_version = 3.11
platform = linux
show_error_codes = true
follow_imports = silent
ignore_missing_imports = true
strict_equality = true
warn_incomplete_stub = true
warn_redundant_casts = true
warn_unused_configs = true
warn_unused_ignores = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = false  # HA uses many untyped decorators
no_implicit_optional = true
warn_return_any = true
no_implicit_reexport = true
strict = true

# Per-module overrides for third-party imports
[mypy-homeassistant.*]
ignore_missing_imports = true
```

**Alternatives Considered**:
- Using `# type:` comments: Rejected - outdated syntax, less readable
- Skipping type hints on internal methods: Rejected - violates constitution principle I
- Using `Any` extensively: Rejected - defeats purpose of type safety

**References**:
- Home Assistant type hints guide: https://developers.home-assistant.io/docs/development_typing/
- PEP 604 (Union syntax): https://peps.python.org/pep-0604/
- PEP 585 (Generic standard collections): https://peps.python.org/pep-0585/
- mypy configuration: https://mypy.readthedocs.io/en/stable/config_file.html

---

### 5. Structured Logging Patterns

**Question**: What are the best practices for structured logging in Home Assistant integrations, especially for error handling and debugging?

**Decision**: Use appropriate log levels with detailed context, follow Home Assistant logging conventions, include operation context and identifiers

**Logging Best Practices**:

**Log Levels**:
```python
import logging
_LOGGER = logging.getLogger(__name__)

# ERROR: Unexpected failures that affect functionality
_LOGGER.error(
    "Failed to process webhook for camera %s (device_id: %s): %s",
    camera_name,
    camera_id,
    exc_info=True,  # Include full traceback
)

# WARNING: Edge cases that are handled but unexpected
_LOGGER.warning(
    "Received malformed webhook data for camera %s: missing 'event_list' field. Data: %s",
    camera_name,
    sanitized_data,  # Sanitize before logging
)

# INFO: Important operational events
_LOGGER.info(
    "Motion detected on camera %s at %s (event types: %s)",
    camera_name,
    event_time,
    event_types,
)

# DEBUG: Detailed operational information
_LOGGER.debug(
    "Processing webhook %s for camera %s with payload size %d bytes",
    webhook_id,
    camera_name,
    payload_size,
)
```

**Context to Include**:
- **Device identifiers**: camera_name, camera_id, device_id
- **Entry identifiers**: entry_id, webhook_id
- **Operation context**: operation name, file being processed, step in workflow
- **Exception details**: exception type, message, traceback (exc_info=True)
- **Relevant data**: sanitized payload snippets, sizes, timestamps

**Error Handling Pattern (FR-021, FR-022, FR-023)**:
```python
async def handle_webhook(hass: HomeAssistant, webhook_id: str, request: Request) -> None:
    try:
        content_type = request.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            try:
                reader = await request.multipart()
                # ... parse multipart
            except asyncio.TimeoutError:
                # FR-021: Network interruption during image transmission
                _LOGGER.warning(
                    "Network timeout while receiving image for camera %s on webhook %s. "
                    "Motion event will be processed without image.",
                    camera_name,
                    webhook_id,
                )
                # Continue processing without image

            except ValueError as e:
                # FR-022: Malformed multipart data
                _LOGGER.warning(
                    "Malformed multipart data for camera %s on webhook %s: %s. "
                    "Attempting to process available parts.",
                    camera_name,
                    webhook_id,
                    str(e),
                )
                # Continue with whatever was parsed

        # Image size validation (FR-023)
        if image_bytes and len(image_bytes) > 5 * 1024 * 1024:  # 5MB
            _LOGGER.warning(
                "Image size (%d bytes) exceeds recommended limit (5MB) for camera %s. "
                "Processing may be slower.",
                len(image_bytes),
                camera_name,
            )
            # Continue processing (don't reject)

    except KeyError as e:
        # Missing required field in JSON
        _LOGGER.warning(
            "Missing required field '%s' in webhook data for camera %s. "
            "Motion event cannot be processed.",
            str(e),
            camera_name,
        )
        return  # Cannot continue without required data

    except Exception as e:
        # Unexpected error - log with full context
        _LOGGER.error(
            "Unexpected error processing webhook for camera %s (webhook_id: %s): %s",
            camera_name,
            webhook_id,
            str(e),
            exc_info=True,  # Full traceback
        )
        # Don't crash - log and return
```

**Data Sanitization**:
- Remove sensitive fields before logging (passwords, tokens, full MAC addresses)
- Truncate large payloads (log first 200 chars + "...")
- Mask IP addresses if privacy concern (log as "192.168.x.x")

**Alternatives Considered**:
- Using print() statements: Rejected - not captured by HA logging system
- Logging everything at DEBUG level: Rejected - makes troubleshooting harder
- Catching all exceptions silently: Rejected - violates constitution principle II

**References**:
- Home Assistant logging: https://developers.home-assistant.io/docs/development_logging/
- Python logging best practices: https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
- Structlog (advanced): Not needed for HA integrations (built-in logging sufficient)

---

## Summary of Decisions

| Research Topic | Decision | Key Impact |
|----------------|----------|------------|
| Image Entity | Use ImageEntity with in-memory byte storage | Enables FR-008, FR-027 |
| Multipart Parsing | aiohttp.MultipartReader with Content-Type detection | Enables FR-010 |
| Webhook UUID | uuid.uuid4() generation, read-only in options | Implements FR-002, FR-003 |
| Type Hints | Comprehensive annotations with mypy strict mode | Constitution principle I compliance |
| Logging | Structured logging with context, specific exceptions | Constitution principle II compliance, FR-020/021/022/023 |

All research topics resolved. No remaining NEEDS CLARIFICATION items. Ready to proceed with Phase 1 design (data-model.md, contracts/, quickstart.md).

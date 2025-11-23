"""Config flow for TP-Link VIGI integration."""

from __future__ import annotations

import logging
import re
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.webhook import async_unregister as webhook_unregister
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import get_url
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_CAMERA_ID,
    CONF_WEBHOOK_ID,
    CONF_RESET_DELAY,
    DEFAULT_RESET_DELAY,
    MIN_RESET_DELAY,
    MAX_RESET_DELAY,
)

_LOGGER = logging.getLogger(__name__)

# Validation pattern for webhook IDs: lowercase letters, numbers, and underscores only
WEBHOOK_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _generate_webhook_id(name: str) -> str:
    """Generate webhook ID from camera name.

    Converts camera name to lowercase and replaces spaces with underscores.
    Example: "Front Door Camera" -> "front_door_camera"
    """
    return name.lower().replace(" ", "_")


def _validate_webhook_id(webhook_id: str) -> bool:
    """Validate webhook ID format.

    Must contain only lowercase letters, numbers, and underscores.
    """
    return bool(WEBHOOK_ID_PATTERN.match(webhook_id))


def _get_base_url(hass: HomeAssistant) -> str:
    """Get base URL for webhook display."""
    try:
        return get_url(hass)
    except (ValueError, KeyError):
        # URL not configured or invalid
        return "http://homeassistant.local:8123"


def _check_duplicate_webhook_id(
    hass: HomeAssistant,
    webhook_id: str,
    exclude_entry_id: str | None = None,
    exclude_cameras: list[dict[str, Any]] | None = None,
) -> bool:
    """Check if webhook ID already exists in any config entry.

    Args:
        hass: Home Assistant instance
        webhook_id: The webhook ID to check
        exclude_entry_id: Optional entry ID to exclude from check
        exclude_cameras: Optional list of cameras to exclude from check

    Returns:
        True if duplicate found, False otherwise
    """
    exclude_cameras = exclude_cameras or []
    exclude_webhook_ids = {cam.get(CONF_WEBHOOK_ID) for cam in exclude_cameras}

    # Check against all existing config entries
    existing_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in existing_entries:
        # Skip excluded entry if specified
        if exclude_entry_id and entry.entry_id == exclude_entry_id:
            continue

        for existing_camera in entry.data.get("cameras", []):
            existing_webhook_id = existing_camera.get(CONF_WEBHOOK_ID)
            if existing_webhook_id == webhook_id and existing_webhook_id not in exclude_webhook_ids:
                return True

    return False


class VigiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TP-Link VIGI."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._cameras: list[dict[str, Any]] = []
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - add first camera."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Get camera name
            camera_name = user_input[CONF_NAME]

            # Auto-generate webhook ID as UUID (FR-002, FR-003)
            webhook_id = str(uuid.uuid4())

            # Check for duplicate webhook ID across all entries (should be extremely rare with UUID)
            if _check_duplicate_webhook_id(self.hass, webhook_id, exclude_cameras=self._cameras):
                # This should never happen with UUIDs, but handle it anyway
                _LOGGER.warning(
                    "Generated duplicate webhook UUID %s (extremely rare). Regenerating.",
                    webhook_id,
                )
                webhook_id = str(uuid.uuid4())

            # Set unique ID for this config entry
            await self.async_set_unique_id(webhook_id)
            self._abort_if_unique_id_configured()

            # Store camera data temporarily with UUID
            self._cameras.append({
                CONF_CAMERA_ID: str(uuid.uuid4()),  # Generate permanent UUID
                CONF_NAME: camera_name,
                CONF_WEBHOOK_ID: webhook_id,
                CONF_RESET_DELAY: user_input.get(CONF_RESET_DELAY, DEFAULT_RESET_DELAY),
            })

            # Show confirmation with webhook URL
            return await self.async_step_confirm()

        # Get base URL for webhook display
        base_url = _get_base_url(self.hass)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Required(
                    CONF_RESET_DELAY,
                    default=DEFAULT_RESET_DELAY
                ): selector({
                    "number": {
                        "min": MIN_RESET_DELAY,
                        "max": MAX_RESET_DELAY,
                        "mode": "box",
                        "unit_of_measurement": "seconds",
                    }
                }),
            }),
            errors=errors,
            description_placeholders={
                "base_url": base_url,
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm camera addition and show webhook URL."""
        if user_input is not None:
            # User confirmed - create the config entry
            return self.async_create_entry(
                title=f"TP-Link VIGI ({len(self._cameras)} camera{'s' if len(self._cameras) > 1 else ''})",
                data={"cameras": self._cameras},
            )

        # Get the most recently added camera
        camera = self._cameras[-1]
        webhook_id = camera[CONF_WEBHOOK_ID]
        camera_name = camera[CONF_NAME]

        # Get base URL for webhook display
        base_url = _get_base_url(self.hass)
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "camera_name": camera_name,
                "webhook_url": webhook_url,
                "webhook_id": webhook_id,
            },
        )



    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VigiOptionsFlow:
        """Get the options flow for this handler."""
        return VigiOptionsFlow(config_entry)


class VigiOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for TP-Link VIGI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._camera_to_edit_idx: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select camera to edit settings."""
        cameras = self.config_entry.data.get("cameras", [])

        if not cameras:
            return self.async_abort(reason="no_cameras")

        # Single camera: skip selection and go straight to edit
        if len(cameras) == 1:
            self._camera_to_edit_idx = 0
            return await self.async_step_edit_camera_form()

        # User selected a camera
        if user_input is not None:
            self._camera_to_edit_idx = user_input["camera_select"]
            return await self.async_step_edit_camera_form()

        # Show camera selection
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("camera_select"): vol.In({
                    idx: f"{cam[CONF_NAME]} ({cam[CONF_WEBHOOK_ID]})"
                    for idx, cam in enumerate(cameras)
                }),
            }),
        )

    async def async_step_edit_camera_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit camera settings form."""
        errors: dict[str, str] = {}
        cameras = self.config_entry.data.get("cameras", [])
        camera = cameras[self._camera_to_edit_idx]

        if user_input is not None:
            new_reset_delay = user_input[CONF_RESET_DELAY]

            # Validate reset delay range
            if not (MIN_RESET_DELAY <= new_reset_delay <= MAX_RESET_DELAY):
                errors[CONF_RESET_DELAY] = "invalid_reset_delay"

            if not errors:
                # Update camera (preserve existing name, webhook_id, and camera_id)
                # Webhook ID is read-only (FR-003)
                cameras[self._camera_to_edit_idx][CONF_RESET_DELAY] = new_reset_delay

                # Update config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={"cameras": cameras},
                )

                # Reload integration
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )

                return self.async_create_entry(title="", data={})

        # Get base URL for webhook display
        base_url = _get_base_url(self.hass)
        webhook_url = f"{base_url}/api/webhook/{camera[CONF_WEBHOOK_ID]}"

        # Show form with current values (webhook_id is read-only, displayed in description)
        return self.async_show_form(
            step_id="edit_camera_form",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_RESET_DELAY,
                    default=camera.get(CONF_RESET_DELAY, DEFAULT_RESET_DELAY)
                ): selector({
                    "number": {
                        "min": MIN_RESET_DELAY,
                        "max": MAX_RESET_DELAY,
                        "mode": "box",
                        "unit_of_measurement": "seconds",
                    }
                }),
            }),
            errors=errors,
            description_placeholders={
                "webhook_id": camera[CONF_WEBHOOK_ID],
                "webhook_url": webhook_url,
                "camera_name": camera[CONF_NAME],
            },
        )

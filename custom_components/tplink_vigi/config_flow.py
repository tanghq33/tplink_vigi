"""Config flow for TP-Link VIGI integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_WEBHOOK_ID

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
            # Get camera name and webhook ID
            camera_name = user_input[CONF_NAME]
            webhook_id = user_input.get(CONF_WEBHOOK_ID)

            # Auto-generate webhook ID if not provided
            if not webhook_id:
                webhook_id = _generate_webhook_id(camera_name)

            # Validate webhook ID format
            if not _validate_webhook_id(webhook_id):
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                # Check for duplicate webhook ID across all entries
                await self.async_set_unique_id(webhook_id)
                self._abort_if_unique_id_configured()

                # Store camera data temporarily
                self._cameras.append({
                    CONF_NAME: camera_name,
                    CONF_WEBHOOK_ID: webhook_id,
                })

                # Show confirmation with webhook URL
                return await self.async_step_confirm()

        # Get base URL for webhook display
        base_url = self.hass.config.api.base_url if self.hass.config.api else "http://homeassistant.local:8123"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_WEBHOOK_ID): cv.string,
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
            if user_input.get("add_another"):
                # Reset unique ID check for next camera
                self._async_abort_entries_match({})
                return await self.async_step_add_another()

            # User clicked "Finish" - create the config entry
            return self.async_create_entry(
                title=f"TP-Link VIGI ({len(self._cameras)} camera{'s' if len(self._cameras) > 1 else ''})",
                data={"cameras": self._cameras},
            )

        # Get the most recently added camera
        camera = self._cameras[-1]
        webhook_id = camera[CONF_WEBHOOK_ID]
        camera_name = camera[CONF_NAME]

        # Get base URL for webhook display
        base_url = self.hass.config.api.base_url if self.hass.config.api else "http://homeassistant.local:8123"
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({
                vol.Optional("add_another", default=False): bool,
            }),
            description_placeholders={
                "camera_name": camera_name,
                "webhook_url": webhook_url,
                "webhook_id": webhook_id,
            },
        )

    async def async_step_add_another(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add another camera to the same config entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Get camera name and webhook ID
            camera_name = user_input[CONF_NAME]
            webhook_id = user_input.get(CONF_WEBHOOK_ID)

            # Auto-generate webhook ID if not provided
            if not webhook_id:
                webhook_id = _generate_webhook_id(camera_name)

            # Validate webhook ID format
            if not _validate_webhook_id(webhook_id):
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                # Check for duplicate in existing cameras
                if any(cam[CONF_WEBHOOK_ID] == webhook_id for cam in self._cameras):
                    errors[CONF_WEBHOOK_ID] = "duplicate_webhook"
                elif any(cam[CONF_NAME] == camera_name for cam in self._cameras):
                    errors[CONF_NAME] = "duplicate_name"
                else:
                    # Check against other config entries
                    existing_entries = self._async_current_entries()
                    for entry in existing_entries:
                        for existing_camera in entry.data.get("cameras", []):
                            if existing_camera.get(CONF_WEBHOOK_ID) == webhook_id:
                                errors[CONF_WEBHOOK_ID] = "duplicate_webhook"
                                break

                    if not errors:
                        # Store camera data
                        self._cameras.append({
                            CONF_NAME: camera_name,
                            CONF_WEBHOOK_ID: webhook_id,
                        })

                        # Show confirmation
                        return await self.async_step_confirm()

        # Get base URL for display
        base_url = self.hass.config.api.base_url if self.hass.config.api else "http://homeassistant.local:8123"

        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_WEBHOOK_ID): cv.string,
            }),
            errors=errors,
            description_placeholders={
                "base_url": base_url,
                "camera_count": str(len(self._cameras)),
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
        self.config_entry = config_entry
        self._camera_to_edit: dict[str, Any] | None = None
        self._camera_to_remove: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_camera", "edit_camera", "remove_camera"],
        )

    async def async_step_add_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new camera."""
        errors: dict[str, str] = {}

        if user_input is not None:
            camera_name = user_input[CONF_NAME]
            webhook_id = user_input.get(CONF_WEBHOOK_ID)

            # Auto-generate webhook ID if not provided
            if not webhook_id:
                webhook_id = _generate_webhook_id(camera_name)

            # Validate webhook ID format
            if not _validate_webhook_id(webhook_id):
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                # Check for duplicates in current entry
                cameras = self.config_entry.data.get("cameras", [])
                if any(cam[CONF_WEBHOOK_ID] == webhook_id for cam in cameras):
                    errors[CONF_WEBHOOK_ID] = "duplicate_webhook"
                elif any(cam[CONF_NAME] == camera_name for cam in cameras):
                    errors[CONF_NAME] = "duplicate_name"
                else:
                    # Check against other entries
                    for entry in self.hass.config_entries.async_entries(DOMAIN):
                        if entry.entry_id == self.config_entry.entry_id:
                            continue
                        for existing_camera in entry.data.get("cameras", []):
                            if existing_camera.get(CONF_WEBHOOK_ID) == webhook_id:
                                errors[CONF_WEBHOOK_ID] = "duplicate_webhook"
                                break

                    if not errors:
                        # Add camera to config entry
                        new_camera = {
                            CONF_NAME: camera_name,
                            CONF_WEBHOOK_ID: webhook_id,
                        }
                        new_cameras = cameras + [new_camera]

                        # Update config entry
                        self.hass.config_entries.async_update_entry(
                            self.config_entry,
                            data={"cameras": new_cameras},
                        )

                        # Reload the integration to create new entities
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                        return self.async_create_entry(title="", data={})

        # Get base URL for display
        base_url = self.hass.config.api.base_url if self.hass.config.api else "http://homeassistant.local:8123"

        return self.async_show_form(
            step_id="add_camera",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_WEBHOOK_ID): cv.string,
            }),
            errors=errors,
            description_placeholders={
                "base_url": base_url,
            },
        )

    async def async_step_edit_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing camera."""
        cameras = self.config_entry.data.get("cameras", [])

        if not cameras:
            return self.async_abort(reason="no_cameras")

        if self._camera_to_edit is None:
            # Show camera selection
            return self.async_show_form(
                step_id="edit_camera",
                data_schema=vol.Schema({
                    vol.Required("camera_select"): vol.In({
                        cam[CONF_WEBHOOK_ID]: f"{cam[CONF_NAME]} ({cam[CONF_WEBHOOK_ID]})"
                        for cam in cameras
                    }),
                }),
            )

        if user_input is not None and "camera_select" in user_input:
            # Camera selected, show edit form
            webhook_id = user_input["camera_select"]
            self._camera_to_edit = next(
                cam for cam in cameras if cam[CONF_WEBHOOK_ID] == webhook_id
            )

            return self.async_show_form(
                step_id="edit_camera_form",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default=self._camera_to_edit[CONF_NAME]): cv.string,
                    vol.Required(CONF_WEBHOOK_ID, default=self._camera_to_edit[CONF_WEBHOOK_ID]): cv.string,
                }),
                description_placeholders={
                    "old_webhook_id": self._camera_to_edit[CONF_WEBHOOK_ID],
                },
            )

        return self.async_abort(reason="unknown_error")

    async def async_step_edit_camera_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the edit camera form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_name = user_input[CONF_NAME]
            new_webhook_id = user_input[CONF_WEBHOOK_ID]

            # Validate webhook ID format
            if not _validate_webhook_id(new_webhook_id):
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                # Check for duplicates (excluding the camera being edited)
                cameras = self.config_entry.data.get("cameras", [])
                for cam in cameras:
                    if cam[CONF_WEBHOOK_ID] == self._camera_to_edit[CONF_WEBHOOK_ID]:
                        continue  # Skip the camera being edited
                    if cam[CONF_WEBHOOK_ID] == new_webhook_id:
                        errors[CONF_WEBHOOK_ID] = "duplicate_webhook"
                    elif cam[CONF_NAME] == new_name:
                        errors[CONF_NAME] = "duplicate_name"

                if not errors:
                    # Update the camera
                    updated_cameras = []
                    for cam in cameras:
                        if cam[CONF_WEBHOOK_ID] == self._camera_to_edit[CONF_WEBHOOK_ID]:
                            updated_cameras.append({
                                CONF_NAME: new_name,
                                CONF_WEBHOOK_ID: new_webhook_id,
                            })
                        else:
                            updated_cameras.append(cam)

                    # Update config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={"cameras": updated_cameras},
                    )

                    # Reload the integration
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="edit_camera_form",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=self._camera_to_edit[CONF_NAME]): cv.string,
                vol.Required(CONF_WEBHOOK_ID, default=self._camera_to_edit[CONF_WEBHOOK_ID]): cv.string,
            }),
            errors=errors,
            description_placeholders={
                "old_webhook_id": self._camera_to_edit[CONF_WEBHOOK_ID],
            },
        )

    async def async_step_remove_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a camera."""
        cameras = self.config_entry.data.get("cameras", [])

        if not cameras:
            return self.async_abort(reason="no_cameras")

        if self._camera_to_remove is None:
            # Show camera selection
            return self.async_show_form(
                step_id="remove_camera",
                data_schema=vol.Schema({
                    vol.Required("camera_select"): vol.In({
                        cam[CONF_WEBHOOK_ID]: f"{cam[CONF_NAME]} ({cam[CONF_WEBHOOK_ID]})"
                        for cam in cameras
                    }),
                }),
            )

        if user_input is not None and "camera_select" in user_input:
            # Camera selected, show confirmation
            webhook_id = user_input["camera_select"]
            self._camera_to_remove = next(
                cam for cam in cameras if cam[CONF_WEBHOOK_ID] == webhook_id
            )

            return self.async_show_form(
                step_id="remove_camera_confirm",
                data_schema=vol.Schema({
                    vol.Required("confirm", default=False): bool,
                }),
                description_placeholders={
                    "camera_name": self._camera_to_remove[CONF_NAME],
                    "webhook_id": self._camera_to_remove[CONF_WEBHOOK_ID],
                },
            )

        return self.async_abort(reason="unknown_error")

    async def async_step_remove_camera_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm camera removal."""
        if user_input is not None:
            if user_input.get("confirm"):
                # Remove the camera
                cameras = self.config_entry.data.get("cameras", [])
                updated_cameras = [
                    cam for cam in cameras
                    if cam[CONF_WEBHOOK_ID] != self._camera_to_remove[CONF_WEBHOOK_ID]
                ]

                # Update config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={"cameras": updated_cameras},
                )

                # Reload the integration
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="", data={})

            # User didn't confirm, go back to init
            return await self.async_step_init()

        return self.async_abort(reason="unknown_error")

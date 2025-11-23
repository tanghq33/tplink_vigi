"""Image platform for TP-Link VIGI cameras."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CAMERA_ID,
    CONF_RESET_DELAY,
    CONF_WEBHOOK_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up image entities from config entry."""
    cameras = entry.data.get("cameras", [])

    images: list[VigiCameraImage] = []

    for camera in cameras:
        camera_name: str = camera[CONF_NAME]
        camera_id: str = camera.get(CONF_CAMERA_ID, "")

        # Ensure camera_id exists (should be set by binary_sensor platform)
        if not camera_id:
            _LOGGER.warning(
                "Camera '%s' missing camera_id. Image entity not created.",
                camera_name,
            )
            continue

        # Create image entity
        image = VigiCameraImage(
            hass, entry, camera_id, camera_name
        )
        images.append(image)

        _LOGGER.info(
            "Created image entity for camera '%s' (camera_id: %s)",
            camera_name,
            camera_id,
        )

    async_add_entities(images, True)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload image entities."""
    # Image entities are automatically cleaned up by Home Assistant
    # No specific cleanup needed beyond entity removal
    return True


class VigiCameraImage(ImageEntity):
    """Representation of a VIGI camera image entity."""

    _attr_has_entity_name: bool = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)
        self._hass = hass
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._attr_name = f"{camera_name} Last Image"
        self._attr_unique_id = f"{entry.entry_id}_{camera_id}_last_image"
        self._attr_content_type = "image/jpeg"  # Default, updated dynamically
        self._image_bytes: bytes | None = None
        self._image_last_updated: datetime | None = None
        self._image_size: int = 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes: dict[str, Any] = {}

        if self._image_last_updated:
            attributes["image_last_updated"] = self._image_last_updated.isoformat()

        if self._image_size > 0:
            attributes["image_size"] = self._image_size

        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this camera."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._camera_id)},
            name=self._camera_name,
            manufacturer="TP-Link",
            model="VIGI Camera",
        )

    async def async_image(self) -> bytes | None:
        """Return bytes of image.

        Reads image data from hass.data storage, populated by webhook handler.
        """
        # Try to get image from hass.data (updated by webhook handler)
        try:
            camera_data = self._hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id]
            image_bytes = camera_data.get("last_image")

            if image_bytes and image_bytes != self._image_bytes:
                # New image available, update internal state
                self._image_bytes = image_bytes
                self._image_last_updated = camera_data.get("last_image_time", dt_util.now())
                self._image_size = camera_data.get("last_image_size", len(image_bytes))

                _LOGGER.debug(
                    "Image entity %s loaded new image: %d bytes",
                    self._attr_name,
                    self._image_size,
                )
        except KeyError:
            # Camera data not found (integration unloaded or camera removed)
            pass

        return self._image_bytes

    def update_image(
        self,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> None:
        """Update the image with new bytes.

        Args:
            image_bytes: Raw image bytes
            content_type: MIME type of the image (e.g., "image/jpeg", "image/png")
        """
        self._image_bytes = image_bytes
        self._attr_content_type = content_type
        self._image_last_updated = dt_util.now()
        self._image_size = len(image_bytes)

        _LOGGER.debug(
            "Updated image for %s: %d bytes (%s)",
            self._attr_name,
            self._image_size,
            content_type,
        )

        # Notify Home Assistant of state change
        self.async_write_ha_state()

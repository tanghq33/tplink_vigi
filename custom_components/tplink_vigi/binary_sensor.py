"""Binary sensor platform for TP-Link VIGI cameras."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
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
    DEFAULT_RESET_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from config entry."""
    cameras = entry.data.get("cameras", [])

    sensors: list[VigiCameraBinarySensor] = []

    for camera in cameras:
        camera_name: str = camera[CONF_NAME]
        webhook_id: str = camera[CONF_WEBHOOK_ID]
        reset_delay: int = camera.get(CONF_RESET_DELAY, DEFAULT_RESET_DELAY)

        # Use permanent camera_id (UUID) for stable device/entity identity
        # If camera_id doesn't exist (old config), generate one and update
        camera_id = camera.get(CONF_CAMERA_ID)
        if not camera_id:
            import uuid
            camera_id = str(uuid.uuid4())
            camera[CONF_CAMERA_ID] = camera_id
            # Update the entry data to persist the UUID
            hass.config_entries.async_update_entry(
                entry,
                data={"cameras": cameras},
            )
            _LOGGER.info(
                "Generated camera_id %s for camera '%s'",
                camera_id,
                camera_name,
            )

        # Store camera data in hass.data for webhook handler access
        hass.data[DOMAIN][entry.entry_id]["cameras"][camera_id] = {
            "name": camera_name,
            "webhook_id": webhook_id,
            "reset_delay": reset_delay,
            "is_on": False,
            "last_event": None,
            "last_event_time": None,
        }

        # Create binary sensor entity
        sensor = VigiCameraBinarySensor(
            hass, entry, camera_id, camera_name, webhook_id, reset_delay
        )
        sensors.append(sensor)

        # Unregister webhook if it already exists (prevents "Handler already defined" error)
        try:
            webhook_unregister(hass, webhook_id)
            _LOGGER.debug("Unregistered existing webhook /api/webhook/%s", webhook_id)
        except Exception:  # noqa: BLE001
            pass  # Webhook doesn't exist, which is fine

        # Register webhook for this camera
        webhook_register(
            hass,
            DOMAIN,
            f"VIGI Camera {camera_name}",
            webhook_id,
            sensor.handle_webhook,
        )

        _LOGGER.info(
            "Registered webhook /api/webhook/%s for camera '%s'",
            webhook_id,
            camera_name,
        )

    async_add_entities(sensors, True)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload binary sensors and unregister webhooks."""
    # CRITICAL: Unregister webhooks based on entry.data (the actual registered webhooks)
    # NOT from hass.data which may have new webhook IDs after config changes
    cameras = entry.data.get("cameras", [])
    for camera in cameras:
        webhook_id = camera.get(CONF_WEBHOOK_ID)
        if webhook_id:
            try:
                webhook_unregister(hass, webhook_id)
                _LOGGER.info("Unregistered webhook /api/webhook/%s", webhook_id)
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug(
                    "Failed to unregister webhook %s: %s (may not exist)",
                    webhook_id,
                    e,
                )

    return True


class VigiCameraBinarySensor(BinarySensorEntity):
    """Representation of a VIGI camera binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_has_entity_name = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
        webhook_id: str,
        reset_delay: int,
    ) -> None:
        """Initialize the binary sensor."""
        self._hass = hass
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._webhook_id = webhook_id
        self._reset_delay = reset_delay
        self._attr_name = f"{camera_name} Motion"
        self._attr_unique_id = f"{entry.entry_id}_{camera_id}_motion"
        self._attr_is_on = False
        self._attributes: dict[str, Any] = {}
        self._reset_task: asyncio.Task | None = None

    @property
    def is_on(self) -> bool:
        """Return true if motion is detected."""
        if self._attr_is_on is None:
            return False
        return self._attr_is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this camera."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._camera_id)},
            name=self._camera_name,
            manufacturer="TP-Link",
            model="VIGI Camera",
            sw_version=self._attributes.get("firmware_version", "Unknown"),
        )

    async def handle_webhook(
        self,
        hass: HomeAssistant,
        webhook_id: str,
        request: Any,
    ) -> None:
        """Handle incoming webhook data from camera."""
        try:
            data: dict[str, Any] = await request.json()

            _LOGGER.debug("Received webhook data for %s: %s", self._attr_name, data)

            device_name: str = data.get("device_name", "Unknown")
            ip: str = data.get("ip", "Unknown")
            mac: str = data.get("mac", "Unknown")
            event_list: list[dict[str, Any]] = data.get("event_list", [])

            if event_list:
                latest_event = event_list[0]
                date_time_str: str = latest_event.get("dateTime", "")
                event_types: list[str] = latest_event.get("event_type", [])

                event_type_str = ", ".join(event_types) if event_types else "unknown"

                # Turn on the binary sensor
                self._attr_is_on = True

                # Parse event time
                event_time = None
                if date_time_str:
                    try:
                        event_time = datetime.strptime(date_time_str, "%Y%m%d%H%M%S")
                        event_time = dt_util.as_local(event_time)
                    except ValueError:
                        _LOGGER.warning(
                            "Could not parse datetime '%s' for %s",
                            date_time_str,
                            self._attr_name,
                        )

                # Update attributes
                self._attributes = {
                    "device_name": device_name,
                    "ip": ip,
                    "mac": mac,
                    "event_type": event_types,
                    "event_type_string": event_type_str,
                    "event_time": event_time.isoformat() if event_time else None,
                    "last_triggered": dt_util.now().isoformat(),
                }

                # Update stored camera data
                try:
                    camera_data = hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id]
                    camera_data["is_on"] = True
                    camera_data["last_event"] = event_types
                    camera_data["last_event_time"] = event_time
                except KeyError:
                    _LOGGER.warning(
                        "Camera data not found for %s (camera_id: %s). "
                        "Webhook may be outdated after configuration change.",
                        self._attr_name,
                        self._camera_id,
                    )

                # Update entity state in Home Assistant
                self.async_write_ha_state()

                _LOGGER.info(
                    "Event detected on %s: %s at %s",
                    self._attr_name,
                    event_type_str,
                    event_time,
                )

                # Cancel any existing reset task
                if self._reset_task and not self._reset_task.done():
                    self._reset_task.cancel()

                # Schedule reset to off after delay
                self._reset_task = asyncio.create_task(self._reset_to_off())

        except Exception as e:  # noqa: BLE001
            _LOGGER.error(
                "Error processing webhook for %s: %s", self._attr_name, e, exc_info=True
            )

    async def _reset_to_off(self) -> None:
        """Reset binary sensor to off state after delay."""
        await asyncio.sleep(self._reset_delay)
        self._attr_is_on = False
        try:
            self._hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id]["is_on"] = False
        except KeyError:
            _LOGGER.debug(
                "Camera data not found for %s during reset. Webhook may be outdated.",
                self._attr_name,
            )
        self.async_write_ha_state()
        _LOGGER.debug("Reset %s to off state", self._attr_name)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        # Cancel reset task if running
        if self._reset_task and not self._reset_task.done():
            self._reset_task.cancel()

        # Clean up camera data
        entry_data = self._hass.data[DOMAIN].get(self._entry.entry_id)
        if entry_data and self._camera_id in entry_data.get("cameras", {}):
            entry_data["cameras"].pop(self._camera_id, None)

        _LOGGER.debug("Cleaned up entity %s", self._attr_name)

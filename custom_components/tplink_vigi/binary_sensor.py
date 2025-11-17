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

from .const import CONF_WEBHOOK_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Time in seconds before resetting sensor back to off
RESET_DELAY = 5


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

        # Use webhook_id as the camera_id for internal tracking
        camera_id = webhook_id

        # Store camera data in hass.data for webhook handler access
        hass.data[DOMAIN][entry.entry_id]["cameras"][camera_id] = {
            "name": camera_name,
            "webhook_id": webhook_id,
            "is_on": False,
            "last_event": None,
            "last_event_time": None,
        }

        # Create binary sensor entity
        sensor = VigiCameraBinarySensor(
            hass, entry, camera_id, camera_name, webhook_id
        )
        sensors.append(sensor)

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
    # Get all cameras for this entry
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data:
        cameras = entry_data.get("cameras", {})
        for camera_id, camera_data in cameras.items():
            webhook_id = camera_data.get("webhook_id")
            if webhook_id:
                webhook_unregister(hass, webhook_id)
                _LOGGER.info("Unregistered webhook /api/webhook/%s", webhook_id)

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
    ) -> None:
        """Initialize the binary sensor."""
        self._hass = hass
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._webhook_id = webhook_id
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
                hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id][
                    "is_on"
                ] = True
                hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id][
                    "last_event"
                ] = event_types
                hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id][
                    "last_event_time"
                ] = event_time

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
        await asyncio.sleep(RESET_DELAY)
        self._attr_is_on = False
        self._hass.data[DOMAIN][self._entry.entry_id]["cameras"][self._camera_id][
            "is_on"
        ] = False
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

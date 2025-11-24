"""TP-Link VIGI Camera Event Integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# This integration only supports config entry setup (UI configuration)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.IMAGE]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the TP-Link VIGI integration from YAML configuration.

    This integration now uses config entries (UI configuration only).
    YAML configuration is no longer supported.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TP-Link VIGI from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize entry data structure
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "cameras": {},
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options flow changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info(
        "TP-Link VIGI integration loaded with %d camera(s)",
        len(entry.data.get("cameras", [])),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up entry data
        hass.data[DOMAIN].pop(entry.entry_id, None)

        _LOGGER.info("TP-Link VIGI integration unloaded")

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options (called when options flow changes are made)."""
    await hass.config_entries.async_reload(entry.entry_id)

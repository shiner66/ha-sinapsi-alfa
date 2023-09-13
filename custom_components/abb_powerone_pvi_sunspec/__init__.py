"""The ABB Power-One PVI SunSpec Integration"""

import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)
from pymodbus.exceptions import ConnectionException

from .api import ABBPowerOnePVISunSpecHub
from .const import (CONF_BASE_ADDR, CONF_HOST, CONF_NAME, CONF_PORT,
                    CONF_SCAN_INTERVAL, CONF_SLAVE_ID, DOMAIN, PLATFORMS,
                    STARTUP_MESSAGE)


_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, entry: Config):
    """Setup of this integration via YAML is not supported"""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI"""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    name = entry.data.get(CONF_NAME)
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT)
    slave_id = entry.data.get(CONF_SLAVE_ID)
    base_addr = entry.data.get(CONF_BASE_ADDR)

    hub = ABBPowerOnePVISunSpecHub(hass, name, host, port, slave_id, base_addr)

    _LOGGER.debug("Setup config entry for ABB")
    coordinator = HubDataUpdateCoordinator(hass, hub=hub, entry=entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    # for platform in PLATFORMS:
    #     if entry.options.get(platform, True):
    #         coordinator.platforms.append(platform)
    #         hass.async_add_job(
    #             hass.config_entries.async_forward_entry_setup(entry, platform)
    #         )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry"""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.unsub()

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry"""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class HubDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub: ABBPowerOnePVISunSpecHub,
        entry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.api = hub
        self.hass = hass
        self.entry = entry
        self.platforms = []
        scan_interval = timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL))
        _LOGGER.debug("Data: %s", entry.data)
        _LOGGER.debug("Options: %s", entry.options)
        self.unsub = entry.add_update_listener(async_reload_entry)
        _LOGGER.debug(
            "Setup entry with scan interval %s. Host: %s Port: %s ID: %s",
            scan_interval,
            entry.data.get(CONF_HOST),
            entry.data.get(CONF_PORT),
            entry.data.get(CONF_SLAVE_ID),
        )
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=scan_interval)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except Exception as exception:
            raise UpdateFailed() from exception


# async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Migrate an old config entry."""
#     version = entry.version

#     # 1-> 2: Migration format
#     if version == 1:
#         hub_name = entry.data.get(CONF_NAME)
#         hub = hass.data[DOMAIN][hub_name]["hub"]
#         # hub.read_sunspec_modbus_init()
#         # hub.read_sunspec_modbus_data()
#         _LOGGER.debug("Migrating from version %s", version)
#         old_uid = entry.unique_id
#         new_uid = hub.data["comm_sernum"]
#         if old_uid != new_uid:
#             hass.config_entries.async_update_entry(
#                 entry, unique_id=new_uid
#             )
#             _LOGGER.debug("Migration to version %s complete: OLD_UID: %s - NEW_UID: %s", entry.version, old_uid, new_uid)
#         if entry.unique_id == new_uid:
#             entry.version = 2
#             _LOGGER.debug("Migration to version %s complete: NEW_UID: %s", entry.version, entry.unique_id)
#     return True

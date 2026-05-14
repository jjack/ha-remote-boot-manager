"""Sensor platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
    ATTR_RECENT_ACTIVITY,
    LOGGER,
    SIGNAL_HOST_REMOVED,
    SIGNAL_HOST_UPDATED,
    SIGNAL_NEW_HOST,
)
from .coordinator import GrubStationCoordinator
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


class GrubStationManagerSensor(CoordinatorEntity[GrubStationCoordinator], SensorEntity):
    """GrubStation sensor class."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: GrubStationCoordinator,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.host = coordinator.host

        self._attr_unique_id = f"{self.host.mac}_last_agent_accessible"
        self._attr_translation_key = "last_agent_accessible"
        self._attr_icon = "mdi:heart-pulse"

        self._attr_device_info = generate_device_info(self.host)

    @property
    def native_value(self) -> str | None:
        """Return the value of the sensor."""
        return self.coordinator.host.last_agent_accessible

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_AGENT_STATUS: self.coordinator.host.agent_status,
            ATTR_HOST_OS: self.coordinator.host.os,
            ATTR_AGENT_SERVICE_MANAGER: self.coordinator.host.agent_service_manager,
            ATTR_AGENT_VERSION: self.coordinator.host.agent_version,
            ATTR_RECENT_ACTIVITY: self.coordinator.host.activity_history,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    manager = entry.runtime_data
    added_hosts: set[str] = set()

    @callback
    def async_add_host_sensor(mac_address: str) -> None:
        """Add a sensor entity for a newly discovered host."""
        if mac_address in added_hosts:
            return

        coordinator = manager.coordinators.get(mac_address)
        if not coordinator:
            return

        host = coordinator.host
        # Only add sensor if host has agent configuration
        if host.agent_is_configured():
            LOGGER.debug("Adding healthcheck sensor for %s", mac_address)
            async_add_entities([GrubStationManagerSensor(coordinator)])
            added_hosts.add(mac_address)

    @callback
    def async_remove_host_sensor(mac_address: str) -> None:
        """Remove a MAC from the tracking set when the host is deleted."""
        added_hosts.discard(mac_address)

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_sensor(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_sensor))
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_HOST_UPDATED, async_add_host_sensor))
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_HOST_REMOVED, async_remove_host_sensor))

"""Sensor platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SIGNAL_NEW_HOST
from .coordinator import GrubStationCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


class GrubStationManagerSensor(CoordinatorEntity[GrubStationCoordinator], SensorEntity):
    """GrubStation sensor class."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: GrubStationCoordinator,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.host = coordinator.data

        self._attr_unique_id = f"{self.host.mac}_last_agent_accessible"
        self._attr_name = "Last Succesful Agent Healthcheck"
        self._attr_icon = "mdi:heart-pulse"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.host.mac)},
            connections={(CONNECTION_NETWORK_MAC, self.host.mac)},
        )

    @property
    def native_value(self) -> str | None:
        """Return the value of the sensor."""
        return self.coordinator.data.last_agent_accessible


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    manager = entry.runtime_data

    @callback
    def async_add_host_sensor(mac_address: str) -> None:
        """Add a sensor entity for a newly discovered host."""
        coordinator = manager.coordinators[mac_address]
        host = coordinator.data
        # Only add sensor if host has agent configuration
        if host.address and host.agent_port and host.api_key:
            async_add_entities([GrubStationManagerSensor(coordinator)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_sensor(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_sensor)
    )

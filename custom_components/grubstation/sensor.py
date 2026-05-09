"""Sensor platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_NEW_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry, RemoteHost


class GrubStationManagerSensor(SensorEntity):
    """GrubStation sensor class."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        host: RemoteHost,
    ) -> None:
        """Initialize the sensor class."""
        self.host = host

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
        return self.host.last_agent_accessible

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self.host.mac}",
                self.async_write_ha_state,
            )
        )


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
        host = manager.hosts[mac_address]
        # Only add sensor if host has agent configuration
        if host.address and host.agent_port and host.api_key:
            async_add_entities([GrubStationManagerSensor(hass, host)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_sensor(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_sensor)
    )

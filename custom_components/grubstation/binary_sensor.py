"""Binary sensor platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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


class GrubStationManagerBinarySensor(
    CoordinatorEntity[GrubStationCoordinator], BinarySensorEntity
):
    """GrubStation binary sensor class."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: GrubStationCoordinator,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.host = coordinator.host

        self._attr_unique_id = f"{self.host.mac}_health_status"
        self._attr_name = "Daemon Status"

        self._attr_device_info = generate_device_info(self.host)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.host.is_daemon_accessible

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_daemon_accessible": self.coordinator.host.last_daemon_accessible,
            "recent_activity": self.coordinator.host.activity_history,
            "os": self.coordinator.host.os,
            "service_manager": self.coordinator.host.daemon_service_manager,
            "version": self.coordinator.host.daemon_version,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    manager = entry.runtime_data
    added_hosts: set[str] = set()

    @callback
    def async_add_host_binary_sensor(mac_address: str) -> None:
        """Add a binary sensor entity for a newly discovered host."""
        if mac_address in added_hosts:
            return

        coordinator = manager.coordinators.get(mac_address)
        if not coordinator:
            return

        host = coordinator.host
        if host and host.daemon_is_configured():
            LOGGER.debug("Adding daemon status binary sensor for %s", mac_address)
            async_add_entities([GrubStationManagerBinarySensor(coordinator)])
            added_hosts.add(mac_address)
        else:
            LOGGER.debug(
                "Skipping binary sensor addition for %s: no daemon info yet",
                mac_address,
            )

    @callback
    def async_remove_host_binary_sensor(mac_address: str) -> None:
        """Remove a MAC from the tracking set when the host is deleted."""
        added_hosts.discard(mac_address)

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_binary_sensor(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_binary_sensor)
    )
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_HOST_UPDATED, async_add_host_binary_sensor
        )
    )
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_HOST_REMOVED, async_remove_host_binary_sensor
        )
    )

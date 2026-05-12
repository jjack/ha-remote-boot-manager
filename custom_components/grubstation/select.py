"""Select platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_BOOT_OPTION_NONE,
    DOMAIN,
    LOGGER,
    SIGNAL_NEW_HOST,
)
from .coordinator import GrubStationCoordinator
from .utils import generate_model_name

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry
    from .manager import GrubStationManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    manager = entry.runtime_data

    @callback
    def async_add_host_select(mac_address: str) -> None:
        """Add a select entity for a newly discovered host."""
        LOGGER.debug("Adding select entity for %s", mac_address)
        coordinator = manager.coordinators[mac_address]
        async_add_entities([GrubStationManagerSelect(manager, coordinator)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_select(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_select)
    )


class GrubStationManagerSelect(CoordinatorEntity[GrubStationCoordinator], SelectEntity):
    """GrubStation select class."""

    def __init__(
        self, manager: GrubStationManager, coordinator: GrubStationCoordinator
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.manager = manager
        self.mac_address = coordinator.host.mac

        # This ties the entity to a specific hardware device in HA
        self._attr_unique_id = f"{self.mac_address}_boot_option_select"
        self._attr_name = "Next Boot Option"
        self._attr_has_entity_name = True

        host_data = coordinator.data

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.mac_address)},
            name=self.mac_address,
            manufacturer="GrubStation",
            model=generate_model_name(host_data),
            sw_version=host_data.daemon_version,
            connections={(CONNECTION_NETWORK_MAC, self.mac_address)},
        )

    @property
    def options(self) -> list[str]:
        """Return the list of available boot options."""
        host_data = self.coordinator.data
        opts = host_data.boot_options if host_data and host_data.boot_options else []

        # Ensure the default "(none)" is always a valid option
        if DEFAULT_BOOT_OPTION_NONE not in opts:
            opts = [DEFAULT_BOOT_OPTION_NONE, *opts]

        return opts

    @property
    def current_option(self) -> str | None:
        """Return the currently pending boot option."""
        host_data = self.coordinator.data
        return (
            host_data.next_boot_option
            if host_data and host_data.next_boot_option
            else DEFAULT_BOOT_OPTION_NONE
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.manager.async_set_next_boot_option(self.mac_address, option)

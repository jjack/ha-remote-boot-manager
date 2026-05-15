"""Select platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SIGNAL_NEW_HOST
from .coordinator import GrubStationCoordinator
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    manager = entry.runtime_data

    @callback
    def async_discover_entities(mac_address: str | None = None) -> None:
        """Add select entities for discovered hosts."""
        if mac_address:
            if coordinator := manager.coordinators.get(mac_address):
                async_add_entities([GrubStationManagerSelect(coordinator)])
        else:
            async_add_entities([GrubStationManagerSelect(coord) for coord in manager.coordinators.values()])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_discover_entities))
    async_discover_entities()


class GrubStationManagerSelect(CoordinatorEntity[GrubStationCoordinator], SelectEntity):
    """GrubStation select class."""

    def __init__(self, coordinator: GrubStationCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.mac_address = self.coordinator.host.mac

        self._attr_unique_id = f"{self.mac_address}_boot_option_select"
        self._attr_name = "Next Boot Option"
        self._attr_has_entity_name = True
        self._attr_device_info = generate_device_info(self.coordinator.host)

    @property
    def options(self) -> list[str]:
        """Return the list of available boot options."""
        return self.coordinator.host.formatted_boot_options

    @property
    def current_option(self) -> str | None:
        """Return the currently pending boot option."""
        return self.coordinator.host.next_boot_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.coordinator.manager.async_set_next_boot_option(self.mac_address, option)

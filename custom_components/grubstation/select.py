"""Select platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_MAC
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    # Only set up if this is a per-host entry
    if not entry.data.get(CONF_MAC):
        return

    coordinator = entry.runtime_data
    async_add_entities([GrubStationManagerSelect(coordinator)])


class GrubStationManagerSelect(CoordinatorEntity, SelectEntity):
    """GrubStation select class."""

    def __init__(self, coordinator) -> None:
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
        await self.coordinator.async_set_next_boot_option(option)

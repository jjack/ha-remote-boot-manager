"""Select platform for Grub OS Selector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DEFAULT_BOOT_OPTION_NONE,
    DOMAIN,
    LOGGER,
    SIGNAL_NEW_HOST,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubOSSelectManagerConfigEntry
    from .manager import GrubOSSelectManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubOSSelectManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    manager = entry.runtime_data

    @callback
    def async_add_host_select(mac_address: str) -> None:
        """Add a select entity for a newly discovered host."""
        LOGGER.debug("Adding select entity for %s", mac_address)
        async_add_entities([GrubOSSelectManagerSelect(manager, mac_address)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_select(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_select)
    )


class GrubOSSelectManagerSelect(SelectEntity):
    """grub_os_selector select class."""

    def __init__(self, manager: GrubOSSelectManager, mac_address: str) -> None:
        """Initialize the select entity."""
        self.manager = manager
        self.mac_address = mac_address

        # This ties the entity to a specific hardware device in HA
        self._attr_unique_id = f"{mac_address}_boot_option_select"
        self._attr_name = "Next Boot Option"
        self._attr_has_entity_name = True

        host_data = self.manager.hosts[mac_address]

        broadcast_info = []
        if broadcast_address := host_data.broadcast_address:
            broadcast_info.append(f"Broadcast: {broadcast_address}")
        if broadcast_port := host_data.broadcast_port:
            broadcast_info.append(f"Port: {broadcast_port}")

        model_name = (
            f"Wake-on-LAN ({', '.join(broadcast_info)})"
            if broadcast_info
            else "Wake-on-LAN"
        )
        if host_data.os_service:
            model_name = f"{host_data.os_service} {model_name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac_address)},
            name=host_data.name,
            manufacturer="Grub OS Selector",
            model=model_name,
            sw_version=host_data.agent_version,
            connections={(CONNECTION_NETWORK_MAC, mac_address)},
        )

    @property
    def options(self) -> list[str]:
        """Return the list of available boot options."""
        host_data = self.manager.hosts.get(self.mac_address)
        opts = host_data.boot_options if host_data and host_data.boot_options else []

        # Ensure the default "(none)" is always a valid option
        if DEFAULT_BOOT_OPTION_NONE not in opts:
            opts = [DEFAULT_BOOT_OPTION_NONE, *opts]

        return opts

    @property
    def current_option(self) -> str | None:
        """Return the currently pending boot option."""
        host_data = self.manager.hosts.get(self.mac_address)
        return (
            host_data.next_boot_option
            if host_data and host_data.next_boot_option
            else DEFAULT_BOOT_OPTION_NONE
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.manager.async_set_next_boot_option(self.mac_address, option)

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        await super().async_added_to_hass()

        # Subscribe to manager updates so the UI redraws when webhooks arrive
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self.mac_address}",
                self.async_write_ha_state,
            )
        )

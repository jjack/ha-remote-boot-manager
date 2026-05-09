"""Binary sensor platform for Grub OS Selector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_NEW_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubOSSelectManagerConfigEntry, RemoteHost


class GrubOSSelectManagerBinarySensor(BinarySensorEntity):
    """Grub OS Selector binary sensor class."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        host: RemoteHost,
    ) -> None:
        """Initialize the binary sensor class."""
        self.host = host

        self._attr_unique_id = f"{self.host.mac}_health_status"
        self._attr_name = "Agent Status"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.host.mac)},
            connections={(CONNECTION_NETWORK_MAC, self.host.mac)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.host.is_agent_accessible

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_agent_accessible": self.host.last_agent_accessible,
        }

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
    entry: GrubOSSelectManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    manager = entry.runtime_data

    @callback
    def async_add_host_binary_sensor(mac_address: str) -> None:
        """Add a binary sensor entity for a newly discovered host."""
        host = manager.hosts[mac_address]
        async_add_entities([GrubOSSelectManagerBinarySensor(hass, host)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_binary_sensor(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_binary_sensor)
    )

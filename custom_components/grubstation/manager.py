"""Coordinator for GrubStation."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SAVE_DELAY
from .coordinator import GrubStationCoordinator
from .data import RemoteHost, WebhookPayload

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class GrubStationManager:
    """Class to manage remote hosts."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Central state manager for remote hosts."""
        self.hass = hass
        self.coordinators: dict[str, GrubStationCoordinator] = {}
        # Keep hosts dict for compatibility with existing tests and logic
        self.hosts: dict[str, RemoteHost] = {}
        self._store = Store(hass, 1, f"{DOMAIN}.hosts")

    @callback
    def async_unload(self) -> None:
        """Stop polling and cleanup."""
        self.coordinators.clear()

    async def async_process_payload(self, mac_address: str, payload: WebhookPayload) -> None:
        """Process incoming payload and update host/coordinator."""
        mac_address = format_mac(mac_address)

        # Find existing coordinator
        coordinator = self.coordinators.get(mac_address)

        if not coordinator:
            # Create a new ConfigEntry for this host
            # This is the modern replacement for the custom Store
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={"mac": mac_address, **payload},
            )
            return

        await coordinator.async_update_host_data(payload)

    @callback
    def async_register_coordinator(self, mac_address: str, coordinator: GrubStationCoordinator) -> None:
        """Register a coordinator for a host."""
        mac_address = format_mac(mac_address)
        self.coordinators[mac_address] = coordinator
        self.hosts[mac_address] = coordinator.host

    @callback
    def async_unregister_coordinator(self, mac_address: str) -> None:
        """Unregister a coordinator for a host."""
        mac_address = format_mac(mac_address)
        self.coordinators.pop(mac_address, None)
        self.hosts.pop(mac_address, None)

    def save(self) -> None:
        """Save data to storage."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        """Return data for storage."""
        return {"hosts": {mac: dataclasses.asdict(host) for mac, host in self.hosts.items()}}

    async def async_load(self) -> None:
        """Load data from storage and initialize coordinators."""
        data = await self._store.async_load()
        if data and "hosts" in data:
            for host_data in data["hosts"].values():
                if isinstance(host_data, dict):
                    valid_keys = {f.name for f in dataclasses.fields(RemoteHost)}
                    filtered_data = {k: v for k, v in host_data.items() if k in valid_keys}
                    # For migration: Import each host as a config entry
                    self.hass.async_create_task(
                        self.hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={"source": "import"},
                            data=filtered_data,
                        )
                    )

    async def async_purge_data(self) -> None:
        """Purge data from storage."""
        self.async_unload()
        self.hosts.clear()
        await self._store.async_remove()

    @callback
    def async_remove_host(self, mac_address: str) -> None:
        """Remove a host from the manager."""
        mac_address = format_mac(mac_address)
        if mac_address in self.hosts:
            self.hosts.pop(mac_address)
            self.coordinators.pop(mac_address, None)
            self.save()

            # Legacy: Find and remove the config entry for this host if it exists
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get("mac") == mac_address:
                    self.hass.async_create_task(self.hass.config_entries.async_remove(entry.entry_id))

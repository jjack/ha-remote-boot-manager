"""Coordinator for GrubStation."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import DOMAIN, LOGGER, SAVE_DELAY, SIGNAL_HOST_REMOVED, SIGNAL_NEW_HOST
from .coordinator import GrubStationCoordinator
from .data import RemoteHost

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class GrubStationManager:
    """Class to manage remote hosts."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Central state manager for remote hosts."""
        self.hass = hass

        self.hosts: dict[str, RemoteHost] = {}
        self.coordinators: dict[str, GrubStationCoordinator] = {}
        self._store = Store(hass, 1, f"{DOMAIN}.hosts")

    async def async_load(self) -> None:
        """Load data from storage and initialize coordinators."""
        data = await self._store.async_load()
        if data and "hosts" in data:
            self.hosts = {}
            for mac, host_data in data["hosts"].items():
                if isinstance(host_data, dict):
                    # Strip unrecognized keys from legacy storage data to prevent
                    # dataclass instantiation errors if the underlying data model has
                    # changed since the data was saved.
                    valid_keys = {f.name for f in dataclasses.fields(RemoteHost)}
                    filtered_data = {k: v for k, v in host_data.items() if k in valid_keys}
                    host = RemoteHost(**filtered_data)
                    self.hosts[mac] = host
                    self.coordinators[mac] = GrubStationCoordinator(self.hass, self, host)
                else:
                    LOGGER.warning(
                        "Discarding invalid host data for %s: %s",
                        mac,
                        host_data,
                    )

        # Start background agent accessibility polling for all coordinators
        for coordinator in self.coordinators.values():
            await coordinator.async_refresh()

    async def async_purge_data(self) -> None:
        """Purge data from storage."""
        self.async_unload()
        self.hosts.clear()
        await self._store.async_remove()

    @callback
    def async_unload(self) -> None:
        """Stop polling and cleanup."""
        self.coordinators.clear()

    @callback
    def async_remove_host(self, mac_address: str) -> None:
        """Remove a host from the manager and save state."""
        mac_address = format_mac(mac_address)
        if mac_address in self.hosts:
            self.hosts.pop(mac_address)
            self.coordinators.pop(mac_address, None)
            self.save()
            LOGGER.info("Removed host: %s", mac_address)
            async_dispatcher_send(self.hass, SIGNAL_HOST_REMOVED, mac_address)
        else:
            LOGGER.debug(
                "Skipping removal: host %s not found in manager. Current hosts: %s",
                mac_address,
                list(self.hosts.keys()),
            )

    def save(self) -> None:
        """Save data to storage."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        """Return data for storage."""
        return {"hosts": {mac: dataclasses.asdict(host) for mac, host in self.hosts.items()}}

    async def async_process_payload(self, mac_address: str, payload: dict[str, Any]) -> None:
        """Process incoming payload and update host/coordinator."""
        mac_address = format_mac(mac_address)
        is_new_host = mac_address not in self.hosts

        if is_new_host:
            host = RemoteHost(mac=mac_address)
            # update_from_payload requires address to be in payload if it's new
            host.update_from_payload(payload)
            self.hosts[mac_address] = host
            coordinator = GrubStationCoordinator(self.hass, self, host)
            self.coordinators[mac_address] = coordinator
            # Fire signal first so entities can be discovered
            async_dispatcher_send(self.hass, SIGNAL_NEW_HOST, mac_address)
            await coordinator.async_refresh()
        else:
            await self.coordinators[mac_address].async_update_host_data(payload)

        self.save()

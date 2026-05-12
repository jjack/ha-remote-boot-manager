"""Coordinator for GrubStation."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    CONF_ADDRESS,
    CONF_PORT,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    CONF_DAEMON_SERVICE_MANAGER,
    CONF_DAEMON_TOKEN,
    CONF_DAEMON_VERSION,
    CONF_HOST_OS,
    DEFAULT_AGENT_PORT,
    DEFAULT_BOOT_OPTION_NONE,
    DOMAIN,
    LOGGER,
    SAVE_DELAY,
    SIGNAL_NEW_HOST,
)
from .coordinator import GrubStationCoordinator
from .data import RemoteHost

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class GrubStationManager:
    """Class to manage remote boot options."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Central state manager for remote boot options."""
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
                    filtered_data = {
                        k: v for k, v in host_data.items() if k in valid_keys
                    }
                    host = RemoteHost(**filtered_data)
                    self.hosts[mac] = host
                    self.coordinators[mac] = GrubStationCoordinator(self.hass, host)
                else:
                    LOGGER.warning(
                        "Discarding invalid host data for %s: %s", mac, host_data
                    )

        # Start background agent accessibility polling for all coordinators
        for coordinator in self.coordinators.values():
            await coordinator.async_config_entry_first_refresh()

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

    def save(self) -> None:
        """Save data to storage."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        """Return data for storage."""
        return {
            "hosts": {mac: dataclasses.asdict(host) for mac, host in self.hosts.items()}
        }

    @callback
    def async_register_daemon(self, mac_address: str, payload: dict[str, Any]) -> None:
        """Process registration payloads from the GrubStation agent."""
        mac_address = format_mac(mac_address)

        if mac_address not in self.hosts:
            host = RemoteHost(
                mac=mac_address,
                address=payload[CONF_ADDRESS],
                agent_port=payload.get(CONF_PORT, DEFAULT_AGENT_PORT),
                daemon_version=payload.get(CONF_DAEMON_VERSION),
                api_key=payload[CONF_DAEMON_TOKEN],
                os=payload.get(CONF_HOST_OS),
                service_manager=payload.get(CONF_DAEMON_SERVICE_MANAGER),
            )
            self.hosts[mac_address] = host
            self.coordinators[mac_address] = GrubStationCoordinator(self.hass, host)

            # Ensure the coordinator has initial data before dispatching SIGNAL_NEW_HOST
            # so that entities created by the signal can access coordinator.data
            # immediately.
            self.coordinators[mac_address].async_set_updated_data(host)

            LOGGER.info("Discovered and registered new host: %s", mac_address)
            async_dispatcher_send(self.hass, SIGNAL_NEW_HOST, mac_address)
        else:
            self.hosts[mac_address].update_from_payload(payload)
            LOGGER.info("Updated registration for host: %s", mac_address)

            # Push the updated data to the coordinator
            self.coordinators[mac_address].async_set_updated_data(
                self.hosts[mac_address]
            )

        self.save()

    @callback
    def async_update_boot_options(
        self, mac_address: str, payload: dict[str, Any]
    ) -> None:
        """Process boot option push payloads from the GrubStation reporter."""
        mac_address = format_mac(mac_address)

        if mac_address not in self.hosts:
            LOGGER.warning(
                "Received boot options for unregistered host: %s. Ignoring.",
                mac_address,
            )
            return

        host = self.hosts[mac_address]
        host.update_from_payload(payload)

        # Ensure "(none)" is the first option
        current_options = host.boot_options
        if not current_options:
            boot_options = [DEFAULT_BOOT_OPTION_NONE]
        elif current_options[0] != DEFAULT_BOOT_OPTION_NONE:
            boot_options = [DEFAULT_BOOT_OPTION_NONE, *current_options]
        else:
            boot_options = current_options

        host.boot_options = boot_options

        # If the selected boot option is no longer in the list, reset it
        if (
            host.next_boot_option not in boot_options
            and host.next_boot_option != DEFAULT_BOOT_OPTION_NONE
        ):
            host.next_boot_option = DEFAULT_BOOT_OPTION_NONE

        LOGGER.info(
            "Received boot options update for host: %s - options: %s",
            mac_address,
            host.boot_options,
        )

        # Push the updated data to the coordinator
        self.coordinators[mac_address].async_set_updated_data(host)
        self.save()

    @callback
    def async_set_next_boot_option(
        self, mac_address: str, next_boot_option: str
    ) -> None:
        """Notify listeners that the selected boot option has changed."""
        mac_address = format_mac(mac_address)
        if mac_address in self.hosts:
            host = self.hosts[mac_address]
            host.next_boot_option = next_boot_option
            self.save()

            # Push the updated data to the coordinator
            self.coordinators[mac_address].async_set_updated_data(host)

            LOGGER.debug(
                "Set selected boot option for %s to %s",
                mac_address,
                next_boot_option,
            )

    @callback
    def async_consume_next_boot_option(self, mac_address: str) -> str:
        """Retrieve the requested boot option and immediately resets the state."""
        mac_address = format_mac(mac_address)
        if mac_address not in self.hosts:
            LOGGER.warning(
                "GRUB requested boot option for unknown MAC address: %s", mac_address
            )
            return DEFAULT_BOOT_OPTION_NONE

        # grab the selected boot option and reset the state for next boot to
        # prevent boot loops
        host = self.hosts[mac_address]
        next_boot_option = host.next_boot_option
        host.next_boot_option = DEFAULT_BOOT_OPTION_NONE
        self.save()

        # Push the updated data to the coordinator
        # This will notify the UI to revert the dropdown back to "(none)"
        self.coordinators[mac_address].async_set_updated_data(host)

        return next_boot_option

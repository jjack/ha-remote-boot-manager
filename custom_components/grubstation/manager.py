"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_PORT,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .agent import async_check_agent_status
from .const import (
    CONF_AGENT_VERSION,
    CONF_BOOT_OPTIONS,
    CONF_OS_SERVICE,
    DEFAULT_AGENT_PORT,
    DEFAULT_BOOT_OPTION_NONE,
    DOMAIN,
    LOGGER,
    SAVE_DELAY,
    SIGNAL_NEW_HOST,
)
from .data import RemoteHost

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class GrubStationManager:
    """Class to manage remote boot options."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Central state manager for remote boot options."""
        self.hass = hass

        self.hosts: dict[str, RemoteHost] = {}
        self._store = Store(hass, 1, f"{DOMAIN}.hosts")
        self._unsub_agent_poll: Any | None = None

    async def async_load(self) -> None:
        """Load data from storage and start agent accessibility polling."""
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
                    self.hosts[mac] = RemoteHost(**filtered_data)
                else:
                    LOGGER.warning(
                        "Discarding invalid host data for %s: %s", mac, host_data
                    )

        # Stop existing polling if re-loading
        if self._unsub_agent_poll:
            self._unsub_agent_poll()

        # Start background agent accessibility polling
        self._unsub_agent_poll = async_track_time_interval(
            self.hass, self.async_poll_agent_status, timedelta(seconds=60)
        )

        # Trigger an initial agent check asynchronously
        self.hass.async_create_task(self.async_poll_agent_status(dt_util.utcnow()))

    async def async_poll_agent_status(self, now: datetime) -> None:
        """Poll the agent status endpoint for all known hosts."""
        for mac, host in self.hosts.items():
            if host.address and host.agent_port and host.api_key:
                is_accessible = await async_check_agent_status(
                    self.hass, host.address, host.agent_port, host.api_key
                )

                state_changed = host.is_agent_accessible != is_accessible
                host.is_agent_accessible = is_accessible

                if is_accessible:
                    host.last_agent_accessible = now.isoformat()
                    # always trigger update if accessible to update
                    # last_agent_accessible
                    state_changed = True

                if state_changed:
                    self.save()
                    async_dispatcher_send(self.hass, f"{DOMAIN}_update_{mac}")

    async def async_purge_data(self) -> None:
        """Purge data from storage."""
        self.async_unload()
        self.hosts.clear()
        await self._store.async_remove()

    @callback
    def async_unload(self) -> None:
        """Stop polling and cleanup."""
        if self._unsub_agent_poll:
            self._unsub_agent_poll()
            self._unsub_agent_poll = None

    @callback
    def async_remove_host(self, mac_address: str) -> None:
        """Remove a host from the manager and save state."""
        mac_address = format_mac(mac_address)
        if mac_address in self.hosts:
            self.hosts.pop(mac_address)
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
    def async_process_webhook_payload(
        self, mac_address: str, payload: dict[str, Any]
    ) -> None:
        """Process payloads from the bare-metal GrubStation cli reporters."""
        mac_address = format_mac(mac_address)

        is_new_host = mac_address not in self.hosts
        if is_new_host:
            self.hosts[mac_address] = RemoteHost(
                mac=mac_address,
                address=payload.get(CONF_ADDRESS),
                agent_port=payload.get(CONF_PORT, DEFAULT_AGENT_PORT),
                agent_version=payload.get(CONF_AGENT_VERSION),
                api_key=payload.get(CONF_API_KEY),
                boot_options=payload.get(CONF_BOOT_OPTIONS) or [],
                broadcast_address=payload.get(CONF_BROADCAST_ADDRESS),
                broadcast_port=payload.get(CONF_BROADCAST_PORT),
                os_service=payload.get(CONF_OS_SERVICE),
            )

            LOGGER.info(
                "Discovered new host: %s",
                mac_address,
            )
        else:
            self.hosts[mac_address].update_from_payload(payload)

            LOGGER.info(
                "Received update for host: %s - boot options: %s",
                mac_address,
                self.hosts[mac_address].boot_options,
            )

        # add "(none)" option to the front of the list if it's not already there
        current_options = self.hosts[mac_address].boot_options
        if not current_options:
            boot_options = [DEFAULT_BOOT_OPTION_NONE]
        elif current_options[0] != DEFAULT_BOOT_OPTION_NONE:
            boot_options = [DEFAULT_BOOT_OPTION_NONE, *current_options]
        else:
            # It's already in the correct format
            boot_options = current_options

        self.hosts[mac_address].boot_options = boot_options

        # If the selected boot option is no longer in the list, reset it
        if (
            self.hosts[mac_address].next_boot_option not in boot_options
            and self.hosts[mac_address].next_boot_option != DEFAULT_BOOT_OPTION_NONE
        ):
            # Prevent boot-loops into non-existent OSes if the host's reported
            # options changed (e.g., OS uninstalled).
            self.hosts[mac_address].next_boot_option = DEFAULT_BOOT_OPTION_NONE

        if is_new_host:
            async_dispatcher_send(self.hass, SIGNAL_NEW_HOST, mac_address)
        else:
            async_dispatcher_send(self.hass, f"{DOMAIN}_update_{mac_address}")

        self.save()

    @callback
    def async_set_next_boot_option(
        self, mac_address: str, next_boot_option: str
    ) -> None:
        """Notify listeners that the selected boot option has changed."""
        mac_address = format_mac(mac_address)
        if mac_address in self.hosts:
            self.hosts[mac_address].next_boot_option = next_boot_option
            self.save()
            async_dispatcher_send(self.hass, f"{DOMAIN}_update_{mac_address}")
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
        next_boot_option = self.hosts[mac_address].next_boot_option
        self.hosts[mac_address].next_boot_option = DEFAULT_BOOT_OPTION_NONE
        self.save()

        # Notify UI to revert the dropdown back to "(none)"
        async_dispatcher_send(self.hass, f"{DOMAIN}_update_{mac_address}")

        return next_boot_option

"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

import homeassistant.util.dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from icmplib import async_ping

from .const import (
    DOMAIN,
    LOGGER,
    PING_COUNT,
    PING_TIMEOUT_SECONDS,
)
from .daemon import async_check_daemon_status

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import RemoteHost
    from .manager import GrubStationManager


async def _async_ping_host(address: str) -> bool:
    """Ping the given host asynchronously."""
    try:
        # privileged=False allows pinging without root privileges on most modern systems
        # We cast to Any because icmplib lacks type hints, causing Pylance to
        # misidentify the return type
        result = await cast("Any", async_ping)(
            address, count=PING_COUNT, timeout=PING_TIMEOUT_SECONDS, privileged=False
        )
        LOGGER.debug("Ping result for %s: %s", address, result.is_alive)
    except Exception as err:  # noqa: BLE001
        LOGGER.debug("Ping failed for %s: %s", address, err)
        return False
    else:
        return result.is_alive


class GrubStationCoordinator(DataUpdateCoordinator["RemoteHost"]):
    """Class to manage fetching GrubStation data for a single host."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: GrubStationManager,
        host: RemoteHost,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.manager = manager
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{host.mac}",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> RemoteHost:
        """Fetch data from the host."""
        if not self.host.address:
            LOGGER.debug("Skipping update for %s: no address", self.host.mac)
            return self.host

        # 1. Check if host is alive via ICMP
        is_alive = await _async_ping_host(self.host.address)

        # 2. If alive and has daemon config, check the daemon status
        is_accessible = False
        if is_alive and self.host.daemon_port and self.host.daemon_token:
            is_accessible = await async_check_daemon_status(
                self.hass,
                self.host.address,
                self.host.daemon_port,
                self.host.daemon_token,
            )
            LOGGER.debug(
                "Daemon status for %s (%s): %s",
                self.host.mac,
                self.host.address,
                is_accessible,
            )
        elif is_alive:
            LOGGER.debug(
                "Skipping daemon check for %s: missing port or token", self.host.mac
            )

        # Log accessibility transitions
        if is_accessible != self.host.is_daemon_accessible:
            status = "Online" if is_accessible else "Offline"
            self.manager.async_log_activity(self.host.mac, f"Daemon is {status}")

        # Update the host state
        self.host.is_daemon_accessible = is_accessible
        self.host.is_powered_on = is_alive

        if is_accessible:
            self.host.last_daemon_accessible = dt_util.utcnow().isoformat()

        return self.host

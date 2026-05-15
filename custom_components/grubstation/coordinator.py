"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from .agent import async_get_agent_status
from .const import API_KEY_OS, API_KEY_SERVICE_MANAGER, API_KEY_STATUS, API_KEY_VERSION, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import RemoteHost
    from .manager import GrubStationManager


async def async_check_tcp_reachability(address: str, port: int) -> bool:
    """Check if a host is reachable via TCP socket (Tier 1)."""
    try:
        async with asyncio.timeout(2):
            _, writer = await asyncio.open_connection(address, port)
            writer.close()
            await writer.wait_closed()
            return True
    except TimeoutError, OSError:
        return False


class GrubStationCoordinator(DataUpdateCoordinator["RemoteHost"]):
    """Manage fetching GrubStation data for a single host."""

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
        """Fetch data from the host using two-tiered polling."""
        if not self.host.address or not self.host.agent_port:
            return self.host

        # Tier 1: TCP Reachability
        is_powered_on = await async_check_tcp_reachability(self.host.address, self.host.agent_port)

        # Tier 2: Daemon Health (only if Tier 1 succeeds)
        is_accessible = False
        agent_status = None

        if is_powered_on and self.host.agent_token:
            try:
                agent_status = await async_get_agent_status(
                    self.hass,
                    self.host.address,
                    self.host.agent_port,
                    self.host.agent_token,
                )
                is_accessible = True
            except Exception as err:  # noqa: BLE001
                LOGGER.warning("Agent unhealthy for %s (%s): %s", self.host.mac, self.host.address, err)
                # We don't raise UpdateFailed here because the host is technically "up"
                # but the daemon is failing. Entities can handle this via availability.

        if is_accessible != self.host.is_agent_accessible:
            status = "Online" if is_accessible else "Offline"
            self.manager.async_log_activity(self.host.mac, f"Agent is {status}")

        self.host.is_agent_accessible = is_accessible
        self.host.is_powered_on = is_powered_on

        if is_accessible and agent_status:
            self.host.last_agent_accessible = dt_util.utcnow().isoformat()
            self.host.agent_status = agent_status.get(API_KEY_STATUS)
            self.host.os = agent_status.get(API_KEY_OS)
            self.host.agent_service_manager = agent_status.get(API_KEY_SERVICE_MANAGER)
            self.host.agent_version = agent_status.get(API_KEY_VERSION)

        return self.host

"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from icmplib import async_ping

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from .agent import async_get_agent_status
from .const import (
    API_KEY_OS,
    API_KEY_SERVICE_MANAGER,
    API_KEY_STATUS,
    API_KEY_VERSION,
    DOMAIN,
    LOGGER,
    PING_COUNT,
    PING_TIMEOUT_SECONDS,
)

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

        # 2. If alive and has agent config, check the agent status
        is_accessible = False
        agent_status = None
        if is_alive and self.host.agent_port and self.host.agent_token:
            agent_status = await async_get_agent_status(
                self.hass,
                self.host.address,
                self.host.agent_port,
                self.host.agent_token,
            )
            is_accessible = agent_status is not None
            LOGGER.debug(
                "Agent status for %s (%s): %s",
                self.host.mac,
                self.host.address,
                "accessible" if is_accessible else "not accessible",
            )
        elif is_alive:
            LOGGER.debug("Skipping agent check for %s: missing port or token", self.host.mac)

        # Log accessibility transitions
        if is_accessible != self.host.is_agent_accessible:
            status = "Online" if is_accessible else "Offline"
            self.manager.async_log_activity(self.host.mac, f"Agent is {status}")

        # Update the host state
        self.host.is_agent_accessible = is_accessible
        self.host.is_powered_on = is_alive

        if is_accessible and agent_status:
            self.host.last_agent_accessible = dt_util.utcnow().isoformat()
            self.host.agent_status = agent_status.get(API_KEY_STATUS)
            self.host.os = agent_status.get(API_KEY_OS)
            self.host.agent_service_manager = agent_status.get(API_KEY_SERVICE_MANAGER)
            self.host.agent_version = agent_status.get(API_KEY_VERSION)

        return self.host

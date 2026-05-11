"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

import homeassistant.util.dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from icmplib import async_ping

from .agent import async_check_agent_status
from .const import (
    DOMAIN,
    LOGGER,
    PING_COUNT,
    PING_TIMEOUT_SECONDS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import RemoteHost


async def _async_ping_host(address: str) -> bool:
    """Ping the given host asynchronously."""
    try:
        # privileged=False allows pinging without root privileges on most modern systems
        # We cast to Any because icmplib lacks type hints, causing Pylance to
        # misidentify the return type
        result = await cast("Any", async_ping)(
            address, count=PING_COUNT, timeout=PING_TIMEOUT_SECONDS, privileged=False
        )
    except Exception:  # noqa: BLE001
        return False
    else:
        return result.is_alive


class GrubStationCoordinator(DataUpdateCoordinator["RemoteHost"]):
    """Class to manage fetching GrubStation data for a single host."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: RemoteHost,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{host.mac}",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> RemoteHost:
        """Fetch data from the host."""
        if not self.host.address:
            return self.host

        # 1. Check if host is alive via ICMP
        is_alive = await _async_ping_host(self.host.address)

        # 2. If alive and has agent config, check agent status
        is_accessible = False
        if is_alive and self.host.agent_port and self.host.api_key:
            is_accessible = await async_check_agent_status(
                self.hass, self.host.address, self.host.agent_port, self.host.api_key
            )

        # Update the host state
        self.host.is_agent_accessible = is_accessible
        self.host.is_powered_on = is_alive

        if is_accessible:
            self.host.last_agent_accessible = dt_util.utcnow().isoformat()

        return self.host

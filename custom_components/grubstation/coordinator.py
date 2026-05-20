"""DataUpdateCoordinator for GrubStation."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from .agent import async_get_agent_status
from .const import (
    API_KEY_OS,
    API_KEY_SERVICE_MANAGER,
    API_KEY_STATUS,
    API_KEY_VERSION,
    DEFAULT_BOOT_OPTION_NONE,
    DOMAIN,
    LOGGER,
)

if TYPE_CHECKING:
    from .data import RemoteHost, WebhookPayload
    from .manager import GrubStationManager


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
        """Fetch data from the host."""
        if not self.host.address or not self.host.agent_port or not self.host.agent_token:
            return self.host

        is_accessible = False
        agent_status = None

        try:
            agent_status = await async_get_agent_status(
                self.hass,
                self.host.address,
                self.host.agent_port,
                self.host.agent_token,
            )
            is_accessible = True
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("Agent unreachable for %s (%s): %s", self.host.mac, self.host.address, err)

        if is_accessible != self.host.is_agent_accessible:
            status = "Online" if is_accessible else "Offline"
            self.async_log_activity(f"Agent is {status}")

        self.host.is_agent_accessible = is_accessible
        self.host.is_powered_on = is_accessible

        if is_accessible and agent_status:
            self.host.last_agent_accessible = dt_util.utcnow().isoformat()
            self.host.agent_status = agent_status.get(API_KEY_STATUS)
            self.host.os = agent_status.get(API_KEY_OS)
            self.host.agent_service_manager = agent_status.get(API_KEY_SERVICE_MANAGER)
            self.host.agent_version = agent_status.get(API_KEY_VERSION)

        return self.host

    async def async_update_host_data(self, payload: WebhookPayload) -> None:
        """Update host data from a webhook payload."""
        self.host.update_from_payload(payload)

        # Reset selection if it's no longer valid
        if self.host.next_boot_option not in self.host.formatted_boot_options:
            self.host.next_boot_option = DEFAULT_BOOT_OPTION_NONE

        self.async_set_updated_data(self.host)
        self.manager.save()

    async def async_set_next_boot_option(self, next_boot_option: str) -> None:
        """Set the pending boot option."""
        self.host.next_boot_option = next_boot_option
        self.async_set_updated_data(self.host)
        self.manager.save()

    @callback
    def async_log_activity(self, message: str) -> None:
        """Log an activity message for this host."""
        LOGGER.info("[%s] %s", self.host.mac, message)

        # Dispatch event for logbook
        self.hass.bus.async_fire(
            f"{DOMAIN}_activity",
            {
                "mac": self.host.mac,
                "message": message,
                "host_name": self.host.os or self.host.mac,
            },
        )

    async def async_consume_next_boot_option(self) -> str:
        """Consume the pending boot option and reset state."""
        next_boot_option = self.host.next_boot_option
        self.host.next_boot_option = DEFAULT_BOOT_OPTION_NONE

        if next_boot_option != DEFAULT_BOOT_OPTION_NONE:
            self.async_log_activity(f"Booting into: {next_boot_option}")

        self.async_set_updated_data(self.host)
        self.manager.save()
        return next_boot_option

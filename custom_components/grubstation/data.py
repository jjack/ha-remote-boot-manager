"""Custom types for GrubStation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_PORT,
)

from .const import (
    CONF_AGENT_VERSION,
    CONF_BOOT_OPTIONS,
    CONF_OS_MANAGER,
    DEFAULT_BOOT_OPTION_NONE,
)

if TYPE_CHECKING:
    from .manager import GrubStationManager


@dataclass(slots=True)
class RemoteHost:
    """Represents the state of a remote bare-metal host."""

    mac: str
    address: str | None = None
    agent_version: str | None = None
    agent_port: int | None = None
    api_key: str | None = None
    boot_options: list[str] = field(default_factory=list)
    broadcast_address: str | None = None
    broadcast_port: int | None = None
    os_manager: str | None = None

    # Agent accessibility status
    is_agent_accessible: bool = False
    is_powered_on: bool = False
    last_agent_accessible: str | None = None

    # this comes from the UI, not the webhook
    next_boot_option: str = DEFAULT_BOOT_OPTION_NONE

    # this also comes from the UI
    off_action: list[dict[str, Any]] | None = None

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        """Safely update the host state from incoming webhook data."""
        self.address = payload.get(CONF_ADDRESS, self.address)
        self.agent_version = payload.get(CONF_AGENT_VERSION, self.agent_version)
        self.agent_port = payload.get(CONF_PORT, self.agent_port)
        self.api_key = payload.get(CONF_API_KEY, self.api_key)
        self.boot_options = payload.get(CONF_BOOT_OPTIONS, self.boot_options) or []
        self.broadcast_address = payload.get(
            CONF_BROADCAST_ADDRESS, self.broadcast_address
        )
        self.broadcast_port = payload.get(CONF_BROADCAST_PORT, self.broadcast_port)
        self.os_manager = payload.get(CONF_OS_MANAGER, self.os_manager)


type GrubStationManagerConfigEntry = ConfigEntry["GrubStationManager"]

"""Custom types for GrubStation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_BROADCAST_ADDRESS, CONF_BROADCAST_PORT

from .const import CONF_AGENT_PORT, CONF_AGENT_TOKEN, CONF_BOOT_OPTIONS, DEFAULT_BOOT_OPTION_NONE

if TYPE_CHECKING:
    from .manager import GrubStationManager


@dataclass(slots=True)
class RemoteHost:
    """Represents the state of a remote bare-metal host."""

    mac: str
    address: str | None = None
    agent_version: str | None = None
    agent_status: str | None = None
    agent_port: int | None = None
    agent_token: str | None = None
    boot_options: list[str] = field(default_factory=list)
    broadcast_address: str | None = None
    broadcast_port: int | None = None
    os: str | None = None
    agent_service_manager: str | None = None

    is_agent_accessible: bool = False
    is_powered_on: bool = False
    last_agent_accessible: str | None = None
    next_boot_option: str = DEFAULT_BOOT_OPTION_NONE
    off_action: list[dict[str, Any]] | None = None
    activity_history: list[str] = field(default_factory=list)

    @property
    def formatted_boot_options(self) -> list[str]:
        """Return boot options with (none) prepended for the UI."""
        if not self.boot_options:
            return [DEFAULT_BOOT_OPTION_NONE]
        if self.boot_options[0] == DEFAULT_BOOT_OPTION_NONE:
            return self.boot_options
        return [DEFAULT_BOOT_OPTION_NONE, *self.boot_options]

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        """Safely update the host state from incoming webhook data."""
        self.address = payload.get(CONF_ADDRESS, self.address)
        self.agent_port = payload.get(CONF_AGENT_PORT, self.agent_port)
        self.agent_token = payload.get(CONF_AGENT_TOKEN, self.agent_token)
        self.boot_options = payload.get(CONF_BOOT_OPTIONS, self.boot_options) or []
        self.broadcast_address = payload.get(CONF_BROADCAST_ADDRESS, self.broadcast_address)
        self.broadcast_port = payload.get(CONF_BROADCAST_PORT, self.broadcast_port)

    def agent_is_configured(self) -> bool:
        """Check if the host has an agent configured."""
        return bool(self.address and self.agent_port and self.agent_token)


type GrubStationManagerConfigEntry = ConfigEntry["GrubStationManager"]

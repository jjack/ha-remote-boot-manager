"""Switch platform for GrubStation."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

import wakeonlan

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import CONF_MAC
from homeassistant.helpers.script import Script
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .agent import async_send_turn_off_command
from .const import DOMAIN
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    # Only set up if this is a per-host entry
    if not entry.data.get(CONF_MAC):
        return

    coordinator = entry.runtime_data
    async_add_entities([GrubStationManagerSwitch(hass, coordinator)])


class GrubStationManagerSwitch(CoordinatorEntity, SwitchEntity):
    """GrubStation power switch."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.hass = hass

        self._attr_unique_id = f"{self.coordinator.host.mac}_power_switch"
        self._attr_name = "Power"
        self._attr_has_entity_name = True
        self._attr_device_class = SwitchDeviceClass.SWITCH

        self._turn_off_action = (
            Script(hass, self.coordinator.host.off_action, self.coordinator.host.mac, DOMAIN)
            if self.coordinator.host.off_action
            else None
        )

        self._attr_device_info = generate_device_info(self.coordinator.host)

    @property
    def is_on(self) -> bool:
        """Return true if the host is powered on."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.is_powered_on

    @property
    def assumed_state(self) -> bool:
        """Return True if we can't reliably check the host state."""
        return not (self.coordinator.host.address and self.coordinator.host.agent_port)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.coordinator.async_log_activity("Sending Wake-on-LAN command")

        wol_kwargs = {}
        if self.coordinator.host.broadcast_address:
            wol_kwargs["ip_address"] = self.coordinator.host.broadcast_address
        if self.coordinator.host.broadcast_port:
            wol_kwargs["port"] = self.coordinator.host.broadcast_port

        await self.hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, self.coordinator.host.mac, **wol_kwargs)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self._turn_off_action:
            self.coordinator.async_log_activity("Running shutdown script")
            await self._turn_off_action.async_run(context=getattr(self, "_context", None))
        elif self.coordinator.host.agent_token and self.coordinator.host.address and self.coordinator.host.agent_port:
            self.coordinator.async_log_activity("Sending shutdown command to agent")
            await async_send_turn_off_command(
                self.hass,
                self.coordinator.host.address,
                self.coordinator.host.agent_port,
                self.coordinator.host.agent_token,
            )
        else:
            self.coordinator.async_log_activity("Shutdown requested (no action configured)")

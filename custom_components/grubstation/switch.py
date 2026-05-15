"""Switch platform for GrubStation."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any

import wakeonlan

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.script import Script
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .agent import async_send_turn_off_command
from .const import DOMAIN, SIGNAL_NEW_HOST, WAIT_FOR_HOST_POWER_SECONDS
from .coordinator import GrubStationCoordinator, async_check_tcp_reachability
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
    manager = entry.runtime_data

    @callback
    def async_discover_entities(mac_address: str | None = None) -> None:
        """Add switch entities for discovered hosts."""
        if mac_address:
            if coordinator := manager.coordinators.get(mac_address):
                async_add_entities([GrubStationManagerSwitch(hass, coordinator)])
        elif entities := [GrubStationManagerSwitch(hass, coord) for coord in manager.coordinators.values()]:
            async_add_entities(entities)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_discover_entities))
    async_discover_entities()


class GrubStationManagerSwitch(CoordinatorEntity[GrubStationCoordinator], SwitchEntity):
    """GrubStation power switch."""

    def __init__(self, hass: HomeAssistant, coordinator: GrubStationCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{self.coordinator.host.mac}_power_switch"
        self._attr_name = "Power"
        self._attr_has_entity_name = True
        self._attr_device_class = SwitchDeviceClass.SWITCH

        self._ping_task: asyncio.Task | None = None
        self._turn_off_action = (
            Script(hass, self.coordinator.host.off_action, self.coordinator.host.mac, DOMAIN)
            if self.coordinator.host.off_action
            else None
        )

        self._attr_device_info = generate_device_info(self.coordinator.host)

    @property
    def is_on(self) -> bool:
        """Return true if the host is powered on."""
        return self.coordinator.data.is_powered_on

    @property
    def assumed_state(self) -> bool:
        """Return True if we can't reliably check the host state."""
        return not (self.coordinator.host.address and self.coordinator.host.agent_port)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.coordinator.manager.async_log_activity(self.coordinator.host.mac, "Sending Wake-on-LAN command")

        wol_kwargs = {}
        if self.coordinator.host.broadcast_address:
            wol_kwargs["ip_address"] = self.coordinator.host.broadcast_address
        if self.coordinator.host.broadcast_port:
            wol_kwargs["port"] = self.coordinator.host.broadcast_port

        await self.hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, self.coordinator.host.mac, **wol_kwargs)
        )

        if self.coordinator.host.address and self.coordinator.host.agent_port:
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
            self._ping_task = self.hass.async_create_background_task(
                self._async_verify_state(target_state=True),
                "wol_verify_on",
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self._turn_off_action:
            self.coordinator.manager.async_log_activity(self.coordinator.host.mac, "Running shutdown script")
            await self._turn_off_action.async_run(context=getattr(self, "_context", None))
        elif self.coordinator.host.agent_token and self.coordinator.host.address and self.coordinator.host.agent_port:
            self.coordinator.manager.async_log_activity(self.coordinator.host.mac, "Sending shutdown command to agent")
            await async_send_turn_off_command(
                self.hass,
                self.coordinator.host.address,
                self.coordinator.host.agent_port,
                self.coordinator.host.agent_token,
            )
        else:
            self.coordinator.manager.async_log_activity(
                self.coordinator.host.mac, "Shutdown requested (no action configured)"
            )

        if self.coordinator.host.address and self.coordinator.host.agent_port:
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
            self._ping_task = self.hass.async_create_background_task(
                self._async_verify_state(target_state=False),
                "wol_verify_off",
            )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up background tasks."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        await super().async_will_remove_from_hass()

    async def _async_verify_state(self, *, target_state: bool) -> None:
        """Verify state change after command."""
        try:
            await asyncio.sleep(WAIT_FOR_HOST_POWER_SECONDS)
            for _ in range(36):  # 3 minutes
                is_awake = await async_check_tcp_reachability(
                    self.coordinator.host.address, self.coordinator.host.agent_port
                )
                if is_awake == target_state:
                    verb = "Power On" if target_state else "Power Off"
                    self.coordinator.manager.async_log_activity(self.coordinator.host.mac, f"{verb} verified")
                    await self.coordinator.async_request_refresh()
                    return
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            return

        verb = "Turn On" if target_state else "Turn Off"
        self.coordinator.manager.async_log_activity(
            self.coordinator.host.mac,
            f"Failed to {verb} within 3 minutes (Host did not respond)",
        )

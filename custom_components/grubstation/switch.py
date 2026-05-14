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
from .const import DOMAIN, LOGGER, SIGNAL_HOST_REMOVED, SIGNAL_NEW_HOST, WAIT_FOR_HOST_POWER_SECONDS
from .coordinator import GrubStationCoordinator, _async_ping_host
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


class GrubStationManagerSwitch(CoordinatorEntity[GrubStationCoordinator], SwitchEntity):
    """GrubStation switch class."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: GrubStationCoordinator,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{self.coordinator.host.mac}_power_switch"
        self._attr_name = "Power"
        self._attr_has_entity_name = True
        self._attr_device_class = SwitchDeviceClass.SWITCH

        # Use the initial state from the coordinator
        self._attr_is_on: bool = bool(self.coordinator.host.is_powered_on) if self.coordinator.host else False

        self._ping_task: asyncio.Task | None = None
        self._turn_off_action = (
            Script(hass, self.coordinator.host.off_action, self.coordinator.host.mac, DOMAIN)
            if self.coordinator.host.off_action
            else None
        )

        self._attr_device_info = generate_device_info(self.coordinator.host)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        # If we have an active ping loop (optimistic state), use that.
        # Otherwise, use the coordinator data.
        if self._ping_task and not self._ping_task.done():
            return self._attr_is_on
        return self.coordinator.host.is_powered_on

    @property
    def _ping_target(self) -> str | None:
        """Return the target IP or hostname to ping."""
        return self.coordinator.host.address

    @property
    def assumed_state(self) -> bool:
        """Flag this entity as unverified if we cannot ping it."""
        return not bool(self._ping_target)

    @property
    def should_poll(self) -> bool:
        """Coordinator handles polling."""
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_agent_accessible": self.coordinator.host.last_agent_accessible,
            "os": self.coordinator.host.os,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        self.async_write_ha_state()

        self.coordinator.manager.async_log_activity(self.coordinator.host.mac, "Sending Wake-on-LAN command")

        wol_kwargs = {}
        if self.coordinator.host.broadcast_address is not None:
            wol_kwargs["ip_address"] = self.coordinator.host.broadcast_address
        if self.coordinator.host.broadcast_port is not None:
            wol_kwargs["port"] = self.coordinator.host.broadcast_port

        # wakeonlan uses blocking sockets; offload to an executor thread to prevent
        # stalling the HA event loop.
        await self.hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, self.coordinator.host.mac, **wol_kwargs)
        )

        target = self._ping_target
        if target:
            # Cancel any existing background ping task to prevent UI state flapping
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
            self._ping_task = self.hass.async_create_background_task(
                self._async_ping_loop(target, target_state=True),
                "wol_ping_on",
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._attr_is_on = False
        self.async_write_ha_state()

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

        target = self._ping_target
        if target:
            # Cancel any existing background ping task to prevent UI state flapping
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
            self._ping_task = self.hass.async_create_background_task(
                self._async_ping_loop(target, target_state=False),
                "wol_ping_off",
            )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up background tasks when the entity is removed."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        await super().async_will_remove_from_hass()

    async def _async_ping_loop(self, host: str, *, target_state: bool) -> None:
        """Ping host rapidly for 3 minutes after turn-on/off."""
        try:
            await asyncio.sleep(WAIT_FOR_HOST_POWER_SECONDS)
        except asyncio.CancelledError:
            # Graciously exit if a new power command cancels this background ping loop.
            return

        for _ in range(36):  # 36 iterations * 5 seconds = 180 seconds (3 mins)
            is_awake = await _async_ping_host(host)
            if is_awake == target_state:
                # Log success
                verb = "Power On" if target_state else "Power Off"
                self.coordinator.manager.async_log_activity(self.coordinator.host.mac, f"{verb} verified")

                # Trigger a coordinator refresh to sync all entities
                await self.coordinator.async_request_refresh()
                return
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                # Graciously exit if a new power command cancels this background ping
                # loop.
                return

        # The timeout was reached without the host changing power states;
        # revert the optimistic UI switch state to reflect the failure.
        self._attr_is_on = not target_state
        if self.hass is not None:
            self.async_write_ha_state()

        # Log the failure
        verb = "Turn On" if target_state else "Turn Off"
        self.coordinator.manager.async_log_activity(
            self.coordinator.host.mac,
            f"Failed to {verb} within 3 minutes (Host did not respond to ping)",
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    manager = entry.runtime_data
    added_hosts: set[str] = set()

    @callback
    def async_add_host_switch(mac_address: str) -> None:
        """Add a switch entity for a newly discovered host."""
        if mac_address in added_hosts:
            return

        coordinator = manager.coordinators.get(mac_address)
        if not coordinator:
            return

        LOGGER.debug("Adding power switch for %s", mac_address)
        async_add_entities([GrubStationManagerSwitch(hass, coordinator)])
        added_hosts.add(mac_address)

    @callback
    def async_remove_host_switch(mac_address: str) -> None:
        """Remove a MAC from the tracking set when the host is deleted."""
        added_hosts.discard(mac_address)

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_switch(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_switch))
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_HOST_REMOVED, async_remove_host_switch))

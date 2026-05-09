"""Switch platform for GrubStation."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any, cast

import wakeonlan
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.script import Script
from icmplib import async_ping

from .agent import async_send_turn_off_command
from .const import (
    DOMAIN,
    PING_COUNT,
    PING_TIMEOUT_SECONDS,
    SIGNAL_NEW_HOST,
    WAIT_FOR_HOST_POWER_SECONDS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry, RemoteHost


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


class GrubStationManagerSwitch(SwitchEntity):
    """GrubStation switch class."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: RemoteHost,
    ) -> None:
        """Initialize the switch class."""
        self.host = host

        self._attr_unique_id = f"{self.host.mac}_wake_switch"
        self._attr_name = "Wake"
        self._attr_has_entity_name = True
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_is_on = False

        self._ping_task: asyncio.Task | None = None
        self._turn_off_action = (
            Script(hass, self.host.off_action, self.host.name, DOMAIN)
            if self.host.off_action
            else None
        )

        broadcast_info = []
        if b_addr := self.host.broadcast_address:
            broadcast_info.append(f"Broadcast: {b_addr}")
        if b_port := self.host.broadcast_port:
            broadcast_info.append(f"Port: {b_port}")

        model_name = (
            f"({', '.join(broadcast_info)})" if broadcast_info else "GrubStation"
        )
        if self.host.os_service:
            model_name = f"{self.host.os_service} {model_name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.host.mac)},
            name=self.host.name,
            manufacturer="GrubStation",
            model=model_name,
            sw_version=self.host.agent_version,
            connections={(CONNECTION_NETWORK_MAC, self.host.mac)},
        )

    @property
    def _ping_target(self) -> str | None:
        """Return the target IP or hostname to ping."""
        return self.host.address

    @property
    def assumed_state(self) -> bool:
        """Flag this entity as unverified if we cannot ping it."""
        return not bool(self._ping_target)

    @property
    def should_poll(self) -> bool:
        """Enable polling only if we have a host to ping."""
        return bool(self._ping_target)

    async def async_update(self) -> None:
        """Update entity state via standard polling."""
        target = self._ping_target
        if not target:
            return

        # don't change the state until the ping task is done
        if self._ping_task and not self._ping_task.done():
            return

        self._attr_is_on = await _async_ping_host(target)

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the entity on."""
        self._attr_is_on = True
        self.async_write_ha_state()

        wol_kwargs = {}
        if self.host.broadcast_address is not None:
            wol_kwargs["ip_address"] = self.host.broadcast_address
        if self.host.broadcast_port is not None:
            wol_kwargs["port"] = self.host.broadcast_port

        # wakeonlan uses blocking sockets; offload to an executor thread to prevent
        # stalling the HA event loop.
        await self.hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, self.host.mac, **wol_kwargs)
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

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the entity off."""
        self._attr_is_on = False
        self.async_write_ha_state()

        if self._turn_off_action:
            await self._turn_off_action.async_run(context=self._context)
        elif self.host.api_key and self.host.address and self.host.agent_port:
            await async_send_turn_off_command(
                self.hass, self.host.address, self.host.agent_port, self.host.api_key
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    manager = entry.runtime_data

    @callback
    def async_add_host_switch(mac_address: str) -> None:
        """Add a switch entity for a newly discovered host."""
        host = manager.hosts[mac_address]
        async_add_entities([GrubStationManagerSwitch(hass, host)])

    # Add entities for hosts that already exist in the manager
    for mac in manager.hosts:
        async_add_host_switch(mac)

    # Listen for the signal to add new hosts discovered via webhook
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_HOST, async_add_host_switch)
    )

"""
Custom integration to integrate grub_os_selector with Home Assistant.

For more details about this integration, please refer to
https://github.com/jjack/ha-grub-os-selector
"""

from __future__ import annotations

from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import wakeonlan
from aiohttp import web
from homeassistant.components import webhook as ha_webhook
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_MAC,
    CONF_PORT,
    Platform,
)
from homeassistant.helpers.storage import Store

from .agent import async_send_turn_off_command
from .const import (
    DEFAULT_AGENT_PORT,
    DOMAIN,
    LOGGER,
    WEBHOOK_NAME,
)
from .manager import GrubOSSelectManager
from .views import GrubConfigView
from .webhook import async_validate_webhook_payload

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.device_registry import DeviceEntry

    from .data import GrubOSSelectManagerConfigEntry

SERVICE_SEND_TURN_ON_COMMAND = "send_turn_on_command"
SERVICE_SEND_TURN_OFF_COMMAND = "send_turn_off_command"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

TURN_ON_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT): cv.port,
    }
)

TURN_OFF_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_AGENT_PORT): cv.port,
        vol.Required(CONF_API_KEY): cv.string,
    }
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:  # noqa: ARG001
    """Set up the grub_os_selector component."""
    # Register the unauthenticated GRUB get request view
    # (ie - GET /api/grub_os_selector/{mac_address})   # noqa: ERA001
    hass.http.register_view(GrubConfigView())

    async def send_turn_on_command(call: ServiceCall) -> None:
        """Handle service call to send wake-on-LAN command to a host."""
        mac_address = call.data[CONF_MAC]
        kwargs = {}
        if CONF_BROADCAST_ADDRESS in call.data:
            kwargs["ip_address"] = call.data[CONF_BROADCAST_ADDRESS]
        if CONF_BROADCAST_PORT in call.data:
            kwargs["port"] = call.data[CONF_BROADCAST_PORT]

        # wakeonlan uses blocking sockets; offload to an executor thread to prevent
        # stalling the HA event loop.
        await hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, mac_address, **kwargs)
        )

    async def send_turn_off_command(call: ServiceCall) -> None:
        """Handle service call to send shutdown command to a host."""
        # Required parameters are guaranteed by TURN_OFF_COMMAND_SCHEMA validation
        address: str = call.data[CONF_ADDRESS]
        agent_port: int = call.data[CONF_PORT]
        api_key: str = call.data[CONF_API_KEY]

        await async_send_turn_off_command(hass, address, agent_port, api_key)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TURN_ON_COMMAND,
        send_turn_on_command,
        schema=TURN_ON_COMMAND_SCHEMA,
    )

    # Register our agent's shutdown action
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TURN_OFF_COMMAND,
        send_turn_off_command,
        schema=TURN_OFF_COMMAND_SCHEMA,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubOSSelectManagerConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    manager = GrubOSSelectManager(hass)
    await manager.async_load()
    entry.runtime_data = manager

    async def handle_webhook(
        hass: HomeAssistant,  # noqa: ARG001
        webhook_id: str,  # noqa: ARG001
        request: web.Request,
    ) -> web.Response:
        """Handle incoming boot option push requests."""
        try:
            LOGGER.debug("received webhook request: %s", request)
            payload, error_response = await async_validate_webhook_payload(request)
            if error_response:
                return error_response
            if payload is None:
                return web.Response(
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    text="Unexpected empty payload",
                )
            if CONF_MAC not in payload:
                return web.Response(
                    status=HTTPStatus.BAD_REQUEST,
                    text="MAC address missing from payload",
                )

            manager.async_process_webhook_payload(payload[CONF_MAC], payload)
            return web.Response(status=HTTPStatus.OK, text="OK")
        except Exception:  # noqa: BLE001
            return web.Response(
                status=HTTPStatus.INTERNAL_SERVER_ERROR, text="Internal Server Error"
            )

    # Register the webhook to receive the boot options push requests
    webhook_id = entry.data.get("webhook_id")
    if webhook_id:
        ha_webhook.async_register(
            hass,
            DOMAIN,
            WEBHOOK_NAME,
            webhook_id,
            handle_webhook,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: GrubOSSelectManagerConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    webhook_id = entry.data.get("webhook_id")
    if webhook_id:
        ha_webhook.async_unregister(hass, webhook_id)

    if hasattr(entry, "runtime_data") and entry.runtime_data:
        entry.runtime_data.async_unload()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: GrubOSSelectManagerConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(
    hass: HomeAssistant,
    entry: GrubOSSelectManagerConfigEntry,
) -> None:
    """Handle removal of an entry."""
    # Since async_unload_entry unregisters the webhook and Home Assistant automatically
    # handles device/entity removal, we just need to purge the manager data.
    if hasattr(entry, "runtime_data") and entry.runtime_data:
        await entry.runtime_data.async_purge_data()
    else:
        # Fallback if entry was never loaded
        await Store(hass, 1, f"{DOMAIN}.hosts").async_remove()


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: GrubOSSelectManagerConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """Remove a device from a config entry and clean up manager data."""
    manager = config_entry.runtime_data

    # Extract the MAC address from the device's identifiers
    mac_address = next(
        (
            identifier[1]
            for identifier in device_entry.identifiers
            if identifier[0] == DOMAIN
        ),
        None,
    )

    # Remove the host from our internal state
    if mac_address:
        manager.async_remove_host(mac_address)

    return True

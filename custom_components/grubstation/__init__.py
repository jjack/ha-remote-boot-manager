"""
Custom integration to integrate GrubStation with Home Assistant.

For more details about this integration, please refer to
https://github.com/jjack/ha-grubstation
"""

from __future__ import annotations

from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aiohttp import web
import voluptuous as vol
import wakeonlan

from homeassistant.components import webhook as ha_webhook
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACTION,
    CONF_ADDRESS,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_MAC,
    Platform,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.storage import Store

from .agent import async_send_turn_off_command
from .const import (
    CONF_AGENT_PORT,
    CONF_AGENT_TOKEN,
    CONF_BOOT_OPTIONS,
    CONF_TURN_OFF_ACTION,
    DEFAULT_AGENT_PORT,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DOMAIN,
    LOGGER,
    SIGNAL_NEW_HOST,
    WEBHOOK_NAME,
)
from .coordinator import GrubStationCoordinator
from .data import RemoteHost
from .manager import GrubStationManager
from .views import GrubConfigView
from .webhook import (
    async_parse_webhook_request,
    validate_register_agent_token_payload,
    validate_update_boot_options_payload,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers import device_registry as dr

    from .data import GrubStationManagerConfigEntry

SERVICE_SEND_TURN_ON_COMMAND = "send_turn_on_command"
SERVICE_SEND_TURN_OFF_COMMAND = "send_turn_off_command"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

TURN_ON_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS, default=DEFAULT_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT, default=DEFAULT_BROADCAST_PORT): cv.port,
    }
)

TURN_OFF_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Optional(CONF_AGENT_PORT, default=DEFAULT_AGENT_PORT): cv.port,
        vol.Required(CONF_AGENT_TOKEN): cv.string,
    }
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the GrubStation component."""
    # Note: GrubConfigView requires a functioning http component
    if "http" in hass.config.components:
        hass.http.register_view(GrubConfigView())

    async def send_turn_on_command(call: ServiceCall) -> None:
        """Handle service call to send wake-on-LAN command to a host."""
        mac_address = call.data[CONF_MAC]
        kwargs = {}
        if CONF_BROADCAST_ADDRESS in call.data:
            kwargs["ip_address"] = call.data[CONF_BROADCAST_ADDRESS]
        if CONF_BROADCAST_PORT in call.data:
            kwargs["port"] = call.data[CONF_BROADCAST_PORT]

        await hass.async_add_executor_job(partial(wakeonlan.send_magic_packet, mac_address, **kwargs))

    async def send_turn_off_command(call: ServiceCall) -> None:
        """Handle service call to send shutdown command to a host."""
        address: str = call.data[CONF_ADDRESS]
        agent_port: int = call.data[CONF_AGENT_PORT]
        agent_token: str = call.data[CONF_AGENT_TOKEN]

        await async_send_turn_off_command(hass, address, agent_port, agent_token)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TURN_ON_COMMAND,
        send_turn_on_command,
        schema=TURN_ON_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TURN_OFF_COMMAND,
        send_turn_off_command,
        schema=TURN_OFF_COMMAND_SCHEMA,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    # Check if this is a Host entry or a Global entry
    mac_address = entry.data.get(CONF_MAC)

    if not mac_address:
        # Global Webhook Entry
        manager = GrubStationManager(hass)
        entry.runtime_data = manager

        async def handle_webhook(
            hass: HomeAssistant,
            webhook_id: str,
            request: web.Request,
        ) -> web.Response:
            """Handle incoming boot option push requests."""
            try:
                raw_payload, error_response = await async_parse_webhook_request(request)
                if error_response:
                    return error_response
                if raw_payload is None:
                    return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR, text="Unexpected empty payload")

                action = raw_payload.get(CONF_ACTION)
                if not action:
                    return web.Response(status=HTTPStatus.BAD_REQUEST, text="Missing action in payload")

                try:
                    if action in ("register_agent_token", "update_boot_options"):
                        if action == "register_agent_token":
                            payload = validate_register_agent_token_payload(raw_payload)
                        else:
                            payload = validate_update_boot_options_payload(raw_payload)
                        await manager.async_process_payload(payload[CONF_MAC], payload)
                    else:
                        return web.Response(status=HTTPStatus.BAD_REQUEST, text=f"Unknown action: {action}")
                except vol.Invalid as err:
                    return web.Response(status=HTTPStatus.BAD_REQUEST, text=f"Invalid payload format: {err}")

                # Success
                return web.Response(status=HTTPStatus.OK, text="OK")
            except Exception:  # noqa: BLE001
                LOGGER.exception("Error handling webhook")
                return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR, text="Internal Server Error")

        webhook_id = entry.data.get("webhook_id")
        if webhook_id:
            ha_webhook.async_register(hass, DOMAIN, WEBHOOK_NAME, webhook_id, handle_webhook)

        # Trigger migration/load from legacy Store
        hass.async_create_task(manager.async_load())

        return True

    # Per-Host Entry
    # Find the global manager
    global_entries = hass.config_entries.async_entries(DOMAIN)
    global_manager_entry = next((e for e in global_entries if not e.data.get(CONF_MAC)), None)

    if not global_manager_entry or not hasattr(global_manager_entry, "runtime_data"):
        LOGGER.error("Global GrubStation manager not found or not ready")
        return False

    manager = global_manager_entry.runtime_data

    # Initialize Host and Coordinator
    # Use options as overrides for the basic data
    host_data = {**entry.data, **entry.options}
    host = RemoteHost(
        mac=mac_address,
        address=host_data.get(CONF_ADDRESS),
        agent_port=host_data.get(CONF_AGENT_PORT),
        agent_token=host_data.get(CONF_AGENT_TOKEN),
        boot_options=host_data.get(CONF_BOOT_OPTIONS),
        broadcast_address=host_data.get(CONF_BROADCAST_ADDRESS),
        broadcast_port=host_data.get(CONF_BROADCAST_PORT),
        off_action=host_data.get(CONF_TURN_OFF_ACTION),
    )

    coordinator = GrubStationCoordinator(hass, manager, host)
    entry.runtime_data = coordinator
    manager.async_register_coordinator(mac_address, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Notify listeners that a new host is available (for compatibility)
    async_dispatcher_send(hass, SIGNAL_NEW_HOST, mac_address)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    mac_address = entry.data.get(CONF_MAC)

    if not mac_address:
        # Global Webhook Entry
        webhook_id = entry.data.get("webhook_id")
        if webhook_id:
            ha_webhook.async_unregister(hass, webhook_id)
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            entry.runtime_data.async_unload()
        return True

    # Per-Host Entry
    coordinator = entry.runtime_data
    coordinator.manager.async_unregister_coordinator(mac_address)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
) -> None:
    """Handle removal of an entry."""
    if not entry.data.get(CONF_MAC):
        # If the global entry is removed, purge the store
        await Store(hass, 1, f"{DOMAIN}.hosts").async_remove()


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: GrubStationManagerConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a device from a config entry."""
    # Find the MAC address in device identifiers
    mac_address = None
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN:
            mac_address = identifier[1]
            break

    if mac_address:
        # Find and remove the per-host config entry
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_MAC) == mac_address:
                hass.async_create_task(hass.config_entries.async_remove(entry.entry_id))
                break

    return True

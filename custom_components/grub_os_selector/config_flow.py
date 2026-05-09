"""Adds config flow for GrubOSSelectManager."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.loader import async_get_loaded_integration

from .const import DOMAIN, GRUB_OS_REPORTER_URL

if TYPE_CHECKING:
    from .data import GrubOSSelectManagerConfigEntry


class GrubOSSelectManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GrubOSSelectManager."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._webhook_id: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return GrubOSSelectManagerOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        integration = async_get_loaded_integration(self.hass, DOMAIN)
        if integration.documentation is None:
            return self.async_abort(reason="missing_documentation")

        if user_input is not None:
            # Form has no fields; clicking submit confirms intent and triggers webhook
            # generation.
            self._webhook_id = webhook.async_generate_id()
            return await self.async_step_webhook_info()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors={},
            description_placeholders={
                "agent_url": GRUB_OS_REPORTER_URL,
                "documentation_url": integration.documentation,
            },
        )

    async def async_step_webhook_info(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the generated webhook ID to the user."""
        if user_input is not None:
            return self.async_create_entry(
                title="Grub OS Selector", data={"webhook_id": self._webhook_id}
            )

        webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)

        return self.async_show_form(
            step_id="webhook_info",
            description_placeholders={
                "webhook_id": self._webhook_id,
                "webhook_url": webhook_url,
                "agent_url": GRUB_OS_REPORTER_URL,
            },
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        if user_input is not None:
            # Form has no fields; clicking submit confirms intent and triggers webhook
            # sgeneration.
            self._webhook_id = webhook.async_generate_id()
            return await self.async_step_reconfigure_webhook_info()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({}),
        )

    async def async_step_reconfigure_webhook_info(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the new webhook ID to the user."""
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data={"webhook_id": self._webhook_id},
            )

        webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)

        return self.async_show_form(
            step_id="reconfigure_webhook_info",
            description_placeholders={
                "webhook_id": self._webhook_id,
                "webhook_url": webhook_url,
                "agent_url": GRUB_OS_REPORTER_URL,
            },
        )


class GrubOSSelectManagerOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Grub OS Selector."""

    def __init__(self, config_entry: GrubOSSelectManagerConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.selected_mac: str | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        manager = self._config_entry.runtime_data

        menu_options = ["view_webhook"]
        if manager and manager.hosts:
            menu_options.insert(0, "select_host")
            menu_description = "What would you like to do?"
        else:
            menu_description = (
                "No hosts have checked in yet. Once a host pings Home Assistant "
                "using the Webhook ID, it will appear here for configuration."
            )

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={"menu_description": menu_description},
        )

    async def async_step_select_host(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select a host to configure."""
        manager = self._config_entry.runtime_data

        if user_input is not None:
            if host := user_input.get("host"):
                self.selected_mac = host
                return await self.async_step_host_config()
            return self.async_create_entry(title="", data={})

        hosts = {mac: f"{host.name} ({mac})" for mac, host in manager.hosts.items()}

        return self.async_show_form(
            step_id="select_host",
            data_schema=vol.Schema({vol.Required("host"): vol.In(hosts)}),
        )

    async def async_step_view_webhook(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the webhook ID."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})

        webhook_id = self._config_entry.data.get("webhook_id", "Unknown")
        return self.async_show_form(
            step_id="view_webhook",
            description_placeholders={"webhook_id": webhook_id},
        )

    async def async_step_host_config(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure specific host."""
        manager = self._config_entry.runtime_data

        if not self.selected_mac:
            return self.async_abort(reason="no_hosts")

        host = manager.hosts[self.selected_mac]

        if user_input is not None:
            host.off_action = user_input.get("turn_off_action")
            if not host.off_action:
                host.off_action = None

            host.address = user_input.get(CONF_ADDRESS)
            host.broadcast_address = user_input.get(CONF_BROADCAST_ADDRESS)
            host.broadcast_port = user_input.get(CONF_BROADCAST_PORT)

            # Persist the changes to storage
            manager.save()

            # Saving the entry data with a timestamp forces Home Assistant to trigger
            # the reload listener
            return self.async_create_entry(title="", data={"updated_at": time.time()})

        default_action = host.off_action or vol.UNDEFINED

        data_schema = {}

        data_schema[
            vol.Optional(
                "turn_off_action",
                description={"suggested_value": default_action},
            )
        ] = selector.ActionSelector({})

        # Address values can be edited here for debugging but will be overwritten the
        # next time the reporter checks in.
        data_schema[
            vol.Optional(CONF_ADDRESS, description={"suggested_value": host.address})
            if host.address is not None
            else vol.Optional(CONF_ADDRESS)
        ] = str
        data_schema[
            vol.Optional(
                CONF_BROADCAST_ADDRESS,
                description={"suggested_value": host.broadcast_address},
            )
            if host.broadcast_address is not None
            else vol.Optional(CONF_BROADCAST_ADDRESS)
        ] = str
        data_schema[
            vol.Optional(
                CONF_BROADCAST_PORT,
                description={"suggested_value": host.broadcast_port},
            )
            if host.broadcast_port is not None
            else vol.Optional(CONF_BROADCAST_PORT)
        ] = int

        return self.async_show_form(
            step_id="host_config",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                "host_name": host.name,
            },
        )

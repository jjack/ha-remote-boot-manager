"""Adds config flow for GrubStationManager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.const import CONF_ADDRESS, CONF_BROADCAST_ADDRESS, CONF_BROADCAST_PORT, CONF_MAC
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.loader import async_get_loaded_integration

from .const import (
    CONF_TURN_OFF_ACTION,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DOMAIN,
    GRUBSTATION_AGENT_URL,
)

if TYPE_CHECKING:
    from .data import GrubStationManagerConfigEntry


class GrubStationManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GrubStationManager."""

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
        return GrubStationManagerOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        # Check if the "Global" entry (which holds the webhook) exists
        if any(not entry.data.get(CONF_MAC) for entry in self._async_current_entries()):
            return self.async_abort(reason="already_configured")

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        if integration.documentation is None:
            return self.async_abort(reason="missing_documentation")

        if user_input is not None:
            self._webhook_id = webhook.async_generate_id()
            return await self.async_step_webhook_info()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors={},
            description_placeholders={
                "agent_url": GRUBSTATION_AGENT_URL,
                "documentation_url": integration.documentation,
            },
        )

    async def async_step_webhook_info(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the generated webhook ID to the user."""
        if user_input is not None:
            return self.async_create_entry(title="GrubStation", data={"webhook_id": self._webhook_id})

        webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)

        return self.async_show_form(
            step_id="webhook_info",
            description_placeholders={
                "webhook_id": self._webhook_id,
                "webhook_url": webhook_url,
                "agent_url": GRUBSTATION_AGENT_URL,
            },
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Import a host as a config entry."""
        mac = import_data.get(CONF_MAC)
        if not mac:
            return self.async_abort(reason="invalid_import_data")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Host {mac}",
            data=import_data,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        if user_input is not None:
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
                "agent_url": GRUBSTATION_AGENT_URL,
            },
        )


class GrubStationManagerOptionsFlow(config_entries.OptionsFlow):
    """Options flow for GrubStation."""

    def __init__(self, config_entry: GrubStationManagerConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        # If this is a per-host entry, show host config
        if self._config_entry.data.get(CONF_MAC):
            return await self.async_step_host_config(user_input)

        # Global entry menu - only show webhook info
        if user_input is not None:
            return await self.async_step_view_webhook()

        return self.async_show_menu(
            step_id="init",
            menu_options=["view_webhook"],
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

    async def async_step_host_config(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Configure specific host."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options to get the most relevant current values
        config = {**self._config_entry.data, **self._config_entry.options}

        data_schema = {
            vol.Optional(
                CONF_TURN_OFF_ACTION,
                description={"suggested_value": config.get(CONF_TURN_OFF_ACTION)},
            ): selector.ActionSelector({}),
            vol.Optional(
                CONF_ADDRESS,
                description={"suggested_value": config.get(CONF_ADDRESS)},
            ): str,
            vol.Optional(
                CONF_BROADCAST_ADDRESS,
                description={
                    "suggested_value": config.get(CONF_BROADCAST_ADDRESS, DEFAULT_BROADCAST_ADDRESS)
                },
            ): str,
            vol.Optional(
                CONF_BROADCAST_PORT,
                description={"suggested_value": config.get(CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT)},
            ): int,
        }

        return self.async_show_form(
            step_id="host_config",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                "host_name": self._config_entry.data.get(CONF_MAC, "Host"),
            },
        )

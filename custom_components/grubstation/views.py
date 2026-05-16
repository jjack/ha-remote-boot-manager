"""Views for the GrubStation custom component."""

from __future__ import annotations

from http import HTTPStatus
import logging

from aiohttp import web

from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.http import HomeAssistantView

from .const import DEFAULT_BOOT_OPTION_NONE, DOMAIN, GRUB_VIEW_URL

LOGGER = logging.getLogger(__package__)


class GrubConfigView(HomeAssistantView):
    """View to handle unauthenticated GRUB requests."""

    # {mac_address} matches the `mac_address` argument to the get method
    url = GRUB_VIEW_URL
    name = f"api:{DOMAIN}:grub_config"
    requires_auth = False

    async def get(self, request: web.Request, mac_address: str) -> web.Response:
        """
        Handle GET requests for a specific host's boot configuration.

            This endpoint deviates from RESTful principles by containing a side-effect:
            it strictly consumes the next_boot_option and resets it to none immediately
            to prevent boot loops, as GRUB only supports HTTP GET.
        """
        hass = request.app["hass"]

        try:
            mac_address = format_mac(mac_address)
        except ValueError:
            return web.Response(text="Invalid MAC address format", status=HTTPStatus.BAD_REQUEST)

        error_msg = None
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        entries = None
        manager = None
        host = None

        if not mac_address:
            error_msg, status = "Invalid MAC address format", HTTPStatus.BAD_REQUEST
        elif not (entries := hass.config_entries.async_entries(DOMAIN)):
            error_msg = "Integration not configured"
        elif not (manager := entries[0].runtime_data):
            error_msg = "Integration not ready"
        elif not (host := manager.hosts.get(mac_address)):
            LOGGER.warning("GRUB request for unknown MAC address: %s", mac_address)
            error_msg, status = "Host not found", HTTPStatus.NOT_FOUND

        if error_msg or not host or not manager or not entries:
            return web.Response(text=error_msg or "Internal Server Error", status=status)

        entry = entries[0]
        expected_token = entry.data.get("webhook_id")
        provided_token = request.query.get("token")

        if not expected_token or provided_token != expected_token:
            LOGGER.warning(
                "Unauthorized GRUB request for MAC %s (invalid or missing token)",
                mac_address,
            )
            return web.Response(text="", content_type="text/plain")

        try:
            # Strictly consume the boot option
            coordinator = manager.coordinators[mac_address]
            next_boot_option = await coordinator.async_consume_next_boot_option()

            if next_boot_option != DEFAULT_BOOT_OPTION_NONE:
                # Escape single quotes to prevent GRUB command injection or syntax
                # errors that could break the boot sequence.
                safe_option = next_boot_option.replace("'", "\\'")
                content = f"set default='{safe_option}'\n"
            else:
                content = ""

            return web.Response(text=content, content_type="text/plain")
        except Exception:
            LOGGER.exception("Error generating boot config for %s", mac_address)
            return web.Response(text="Internal Server Error", status=HTTPStatus.INTERNAL_SERVER_ERROR)

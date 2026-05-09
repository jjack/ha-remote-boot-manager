"""Webhook handlers for grub_os_selector."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, cast

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import web
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
)
from homeassistant.helpers.device_registry import format_mac

from .const import (
    CONF_AGENT_VERSION,
    CONF_BOOT_OPTIONS,
    CONF_OS_SERVICE,
    DEFAULT_AGENT_PORT,
    LOGGER,
    WEBHOOK_MAX_PAYLOAD_BYTES,
)

WEBHOOK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_MAC): format_mac,
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Required(CONF_BOOT_OPTIONS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_AGENT_VERSION): cv.string,
        vol.Optional(CONF_OS_SERVICE): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT): cv.port,
        vol.Optional(CONF_PORT, default=DEFAULT_AGENT_PORT): cv.port,
        vol.Optional(CONF_API_KEY): cv.string,
    }
)


async def async_validate_webhook_payload(
    request: web.Request,
) -> tuple[dict[str, Any] | None, web.Response | None]:
    """Validate and parse incoming webhook payload."""
    body = await request.text()
    if not body:
        LOGGER.warning("Ignoring Grub OS Selector push request webhook with empty body")
        return None, web.Response(status=HTTPStatus.BAD_REQUEST, text="empty body")

    if len(body) > WEBHOOK_MAX_PAYLOAD_BYTES:
        LOGGER.warning("Webhook payload too large")
        return None, web.Response(
            status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, text="Payload too large"
        )

    try:
        raw_payload = json.loads(body)
    except json.JSONDecodeError:
        LOGGER.warning("Webhook payload is not valid JSON")
        LOGGER.debug("Received invalid JSON payload: %s", body)
        return None, web.Response(
            status=HTTPStatus.BAD_REQUEST, text="Invalid JSON payload"
        )

    LOGGER.debug("Received Grub OS Selector webhook with payload: %s", raw_payload)

    try:
        # Use cast to force the type checker to treat the output as a dict
        payload = cast("dict[str, Any]", WEBHOOK_SCHEMA(raw_payload))
    except vol.Invalid as err:
        LOGGER.warning("Invalid webhook schema from incoming request: %s", err)
        return None, web.Response(
            status=HTTPStatus.BAD_REQUEST, text=f"Invalid payload format: {err}"
        )

    if not payload.get(CONF_NAME):
        # Ensure a name exists for UI presentation, falling back to the network address
        # if the reporter omitted it.
        payload[CONF_NAME] = payload[CONF_ADDRESS]

    return payload, None

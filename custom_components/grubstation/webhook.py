"""Webhook handlers for GrubStation."""

from __future__ import annotations

from http import HTTPStatus
import json
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.const import CONF_ACTION, CONF_ADDRESS, CONF_BROADCAST_ADDRESS, CONF_BROADCAST_PORT, CONF_MAC
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import format_mac

from .const import (
    CONF_AGENT_PORT,
    CONF_AGENT_TOKEN,
    CONF_BOOT_OPTIONS,
    DEFAULT_AGENT_PORT,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    LOGGER,
    WEBHOOK_MAX_PAYLOAD_BYTES,
)
from .data import WebhookPayload

BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACTION): cv.string,
        vol.Required(CONF_MAC): format_mac,
        vol.Required(CONF_ADDRESS): cv.string,
    }
)

REGISTER_AGENT_TOKEN_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required(CONF_AGENT_PORT, default=DEFAULT_AGENT_PORT): cv.port,
        vol.Required(CONF_AGENT_TOKEN): cv.string,
    }
)

UPDATE_BOOT_OPTIONS_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required(CONF_BOOT_OPTIONS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_BROADCAST_ADDRESS, default=DEFAULT_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT, default=DEFAULT_BROADCAST_PORT): cv.port,
    }
)


async def async_parse_webhook_request(
    request: web.Request,
) -> tuple[WebhookPayload | None, web.Response | None]:
    """Parse and perform basic validation on the incoming webhook request."""
    body = await request.text()
    if not body:
        LOGGER.warning("Ignoring GrubStation push request webhook with empty body")
        return None, web.Response(status=HTTPStatus.BAD_REQUEST, text="empty body")

    if len(body) > WEBHOOK_MAX_PAYLOAD_BYTES:
        LOGGER.warning("Webhook payload too large")
        return None, web.Response(status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, text="Payload too large")

    try:
        raw_payload = json.loads(body)
    except json.JSONDecodeError:
        LOGGER.warning("Webhook payload is not valid JSON")
        LOGGER.debug("Received invalid JSON payload: %s", body)
        return None, web.Response(status=HTTPStatus.BAD_REQUEST, text="Invalid JSON payload")

    if not isinstance(raw_payload, dict):
        LOGGER.warning("Webhook payload is not a JSON object")
        return None, web.Response(status=HTTPStatus.BAD_REQUEST, text="Payload must be a JSON object")

    LOGGER.debug("Received GrubStation webhook with payload: %s", raw_payload)
    return raw_payload, None


def validate_register_agent_token_payload(payload: dict[str, Any]) -> WebhookPayload:
    """Validate a register_agent_token webhook payload."""
    return REGISTER_AGENT_TOKEN_SCHEMA(payload)


def validate_update_boot_options_payload(payload: dict[str, Any]) -> WebhookPayload:
    """Validate a update_boot_options webhook payload."""
    return UPDATE_BOOT_OPTIONS_SCHEMA(payload)

"""Tests for webhook functionality."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from aiohttp import web

from custom_components.grubstation.webhook import (
    async_parse_webhook_request,
    validate_register_daemon_token_payload,
    validate_update_boot_options_payload,
)


async def test_parse_webhook_empty_body():
    """Test parsing with empty body."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="")

    payload, response = await async_parse_webhook_request(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text == "empty body"


async def test_parse_webhook_payload_too_large():
    """Test parsing with oversized payload."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="a" * 102401)

    payload, response = await async_parse_webhook_request(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


async def test_parse_webhook_invalid_json():
    """Test parsing with invalid JSON."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="invalid json")

    payload, response = await async_parse_webhook_request(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text == "Invalid JSON payload"


async def test_parse_webhook_not_an_object():
    """Test parsing with valid JSON but not an object."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value='["not", "an", "object"]')

    payload, response = await async_parse_webhook_request(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text == "Payload must be a JSON object"


async def test_parse_webhook_valid_payload():
    """Test parsing with valid payload."""
    request = MagicMock(spec=web.Request)
    valid_data = '{"mac": "00:11:22:33:44:55", "action": "test"}'
    request.text = AsyncMock(return_value=valid_data)

    payload, response = await async_parse_webhook_request(request)
    assert response is None
    assert payload == {"mac": "00:11:22:33:44:55", "action": "test"}


def test_validate_register_daemon_token_payload():
    """Test validation of register_daemon_token payload."""
    valid_payload = {
        "action": "register_daemon_token",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "host_os": "linux",
        "daemon_port": 8000,
        "daemon_token": "secret",
        "daemon_version": "1.0.0",
    }
    validated = validate_register_daemon_token_payload(valid_payload)
    assert validated["mac"] == "00:11:22:33:44:55"
    assert validated["daemon_port"] == 8000

    invalid_payload = {"action": "register_daemon_token", "mac": "invalid"}
    with pytest.raises(vol.Invalid):
        validate_register_daemon_token_payload(invalid_payload)


def test_validate_update_boot_options_payload():
    """Test validation of update_boot_options payload."""
    valid_payload = {
        "action": "update_boot_options",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "host_os": "linux",
        "daemon_version": "1.0.0",
        "boot_options": ["ubuntu", "windows"],
    }
    validated = validate_update_boot_options_payload(valid_payload)
    assert validated["mac"] == "00:11:22:33:44:55"
    assert validated["boot_options"] == ["ubuntu", "windows"]

    invalid_payload = {
        "action": "update_boot_options",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "host_os": "linux",
        "daemon_version": "1.0.0",
        "boot_options": {"not": "a list"},
    }
    with pytest.raises(vol.Invalid):
        validate_update_boot_options_payload(invalid_payload)

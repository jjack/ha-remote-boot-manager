"""Tests for webhook functionality."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

from aiohttp import web

from custom_components.grubstation.webhook import async_validate_webhook_payload


async def test_validate_webhook_empty_body():
    """Test validation with empty body."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="")

    payload, response = await async_validate_webhook_payload(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text == "empty body"


async def test_validate_webhook_payload_too_large():
    """Test validation with oversized payload."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="a" * 102401)

    payload, response = await async_validate_webhook_payload(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


async def test_validate_webhook_invalid_json():
    """Test validation with invalid JSON."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value="invalid json")
    request.json = AsyncMock(side_effect=ValueError("Boom"))

    payload, response = await async_validate_webhook_payload(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text == "Invalid JSON payload"


async def test_validate_webhook_invalid_schema():
    """Test validation with invalid schema."""
    request = MagicMock(spec=web.Request)
    request.text = AsyncMock(return_value='{"address": "test.local"}')  # missing mac
    request.json = AsyncMock(return_value={"address": "test.local"})

    payload, response = await async_validate_webhook_payload(request)
    assert payload is None
    assert response is not None
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.text is not None
    assert "Invalid payload format" in response.text


async def test_validate_webhook_valid_payload():
    """Test validation with valid payload."""
    request = MagicMock(spec=web.Request)
    valid_data = {
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "boot_options": ["ubuntu", "windows"],
        "broadcast_address": "192.168.1.255",
        "broadcast_port": 9,
    }
    request.text = AsyncMock(
        return_value='{"mac": "00:11:22:33:44:55", "address": "test.local", "boot_options": ["ubuntu", "windows"], "broadcast_address": "192.168.1.255", "broadcast_port": 9}'
    )
    request.json = AsyncMock(return_value=valid_data)

    payload, response = await async_validate_webhook_payload(request)
    assert response is None
    assert payload is not None
    assert payload["mac"] == "00:11:22:33:44:55"
    assert payload["address"] == "test.local"
    assert payload["boot_options"] == ["ubuntu", "windows"]
    assert payload["broadcast_address"] == "192.168.1.255"
    assert payload["broadcast_port"] == 9


async def test_validate_webhook_content_type_agnostic():
    """Test validation works regardless of the Content-Type header."""
    valid_json_text = '{"mac": "00:11:22:33:44:55", "address": "test.local", "boot_options": ["ubuntu"]}'

    request_with_header = MagicMock(spec=web.Request)
    request_with_header.headers = {"Content-Type": "application/json"}
    request_with_header.text = AsyncMock(return_value=valid_json_text)

    request_without_header = MagicMock(spec=web.Request)
    request_without_header.headers = {}
    request_without_header.text = AsyncMock(return_value=valid_json_text)

    request_wrong_header = MagicMock(spec=web.Request)
    request_wrong_header.headers = {"Content-Type": "text/plain"}
    request_wrong_header.text = AsyncMock(return_value=valid_json_text)

    # Test all variations to ensure the payload is parsed correctly
    # without relying on aiohttp's strict request.json() content-type checking.
    for request in [request_with_header, request_without_header, request_wrong_header]:
        payload, response = await async_validate_webhook_payload(request)
        assert response is None
        assert payload is not None
        assert payload["mac"] == "00:11:22:33:44:55"

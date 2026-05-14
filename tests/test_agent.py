"""Tests for the GrubStation agent communication."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.grubstation.agent import async_get_agent_status, async_send_turn_off_command
from custom_components.grubstation.const import ATTR_HOST_OS, ATTR_SERVICE_MANAGER, ATTR_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


async def test_async_send_turn_off_command_success(hass: HomeAssistant) -> None:
    """Test successful shutdown command."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_session.post.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        mock_session_getter.return_value = mock_session

        await async_send_turn_off_command(hass, "1.2.3.4", 8081, "secret_key")

        mock_session.post.assert_called_once()
        args, kwargs = mock_session.post.call_args
        url = args[0]
        assert url.host == "1.2.3.4"
        assert url.port == 8081
        assert url.path == "/shutdown"
        assert kwargs["headers"]["Authorization"] == "Bearer secret_key"


async def test_async_send_turn_off_command_agent_error(hass: HomeAssistant) -> None:
    """Test shutdown command handles error status in JSON."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value={"status": "error", "error": "Something went wrong"})
        mock_session.post.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        mock_session_getter.return_value = mock_session

        with pytest.raises(HomeAssistantError, match="Something went wrong"):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "key")


async def test_async_send_turn_off_command_http_error(hass: HomeAssistant) -> None:
    """Test shutdown command handles non-200 responses."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.FORBIDDEN
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=HTTPStatus.FORBIDDEN,
        )
        mock_session.post.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        mock_session_getter.return_value = mock_session

        with pytest.raises(HomeAssistantError, match="Shutdown command failed"):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "wrong_key")


async def test_async_send_turn_off_command_timeout(hass: HomeAssistant) -> None:
    """Test shutdown command handles timeouts."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_session.post.side_effect = TimeoutError()
        mock_session_getter.return_value = mock_session

        with pytest.raises(HomeAssistantError, match="Shutdown command failed"):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "key")


async def test_async_send_turn_off_command_unexpected_error(
    hass: HomeAssistant,
) -> None:
    """Test shutdown command handles unexpected exceptions."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_session.post.side_effect = RuntimeError("Boom")
        mock_session_getter.return_value = mock_session

        with (
            patch("custom_components.grubstation.agent.LOGGER.exception") as mock_log,
            pytest.raises(HomeAssistantError, match="Shutdown command failed: Boom"),
        ):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "key")

        mock_log.assert_called_once_with("Unexpected error sending shutdown command to %s", "1.2.3.4")


async def test_async_get_agent_status_success(hass: HomeAssistant) -> None:
    """Test successful status check."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(
            return_value={
                ATTR_HOST_OS: "linux",
                ATTR_SERVICE_MANAGER: "systemd",
                ATTR_VERSION: "1.0.0",
            }
        )
        mock_session.get.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        mock_session_getter.return_value = mock_session

        result = await async_get_agent_status(hass, "1.2.3.4", 8081, "secret_key")

        assert result == {
            ATTR_HOST_OS: "linux",
            ATTR_SERVICE_MANAGER: "systemd",
            ATTR_VERSION: "1.0.0",
        }
        mock_session.get.assert_called_once()
        args, kwargs = mock_session.get.call_args
        url = args[0]
        assert url.host == "1.2.3.4"
        assert url.port == 8081
        assert url.path == "/status"
        assert kwargs["headers"]["Authorization"] == "Bearer secret_key"


async def test_async_get_agent_status_failure(hass: HomeAssistant) -> None:
    """Test status check handles failures gracefully."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_session.get.side_effect = TimeoutError()
        mock_session_getter.return_value = mock_session

        result = await async_get_agent_status(hass, "1.2.3.4", 8081, "key")
        assert result is None


async def test_async_get_agent_status_invalid_schema(hass: HomeAssistant) -> None:
    """Test status check handles invalid schema."""
    with patch("custom_components.grubstation.agent.async_get_clientsession") as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(
            return_value={
                "not_os": "something",
            }
        )
        mock_session.get.return_value = AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        mock_session_getter.return_value = mock_session

        result = await async_get_agent_status(hass, "1.2.3.4", 8081, "key")
        assert result is None

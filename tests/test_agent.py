"""Tests for the GrubStation daemon communication."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.grubstation.daemon import (
    async_check_daemon_status,
    async_send_turn_off_command,
)


async def test_async_send_turn_off_command_success(hass: HomeAssistant) -> None:
    """Test successful shutdown command."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_session.post.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response)
        )
        mock_session_getter.return_value = mock_session

        await async_send_turn_off_command(hass, "1.2.3.4", 8081, "secret_key")

        mock_session.post.assert_called_once()
        args, kwargs = mock_session.post.call_args
        url = args[0]
        assert url.host == "1.2.3.4"
        assert url.port == 8081
        assert url.path == "/shutdown"
        assert kwargs["headers"]["Authorization"] == "Bearer secret_key"


async def test_async_send_turn_off_command_http_error(hass: HomeAssistant) -> None:
    """Test shutdown command handles non-200 responses."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.FORBIDDEN
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=HTTPStatus.FORBIDDEN,
        )
        mock_session.post.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response)
        )
        mock_session_getter.return_value = mock_session

        with pytest.raises(HomeAssistantError, match="Shutdown command failed"):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "wrong_key")


async def test_async_send_turn_off_command_timeout(hass: HomeAssistant) -> None:
    """Test shutdown command handles timeouts."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_session.post.side_effect = TimeoutError()
        mock_session_getter.return_value = mock_session

        with pytest.raises(HomeAssistantError, match="Shutdown command failed"):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "key")


async def test_async_send_turn_off_command_unexpected_error(
    hass: HomeAssistant,
) -> None:
    """Test shutdown command handles unexpected exceptions."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_session.post.side_effect = RuntimeError("Boom")
        mock_session_getter.return_value = mock_session

        with (
            patch("custom_components.grubstation.daemon.LOGGER.exception") as mock_log,
            pytest.raises(HomeAssistantError, match="Shutdown command failed: Boom"),
        ):
            await async_send_turn_off_command(hass, "1.2.3.4", 8081, "key")

        mock_log.assert_called_once_with(
            "Unexpected error sending shutdown command to %s", "1.2.3.4"
        )


async def test_async_check_daemon_status_success(hass: HomeAssistant) -> None:
    """Test successful health check."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.text = AsyncMock(return_value="ok\n")
        mock_session.get.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response)
        )
        mock_session_getter.return_value = mock_session

        result = await async_check_daemon_status(hass, "1.2.3.4", 8081, "secret_key")

        assert result is True
        mock_session.get.assert_called_once()
        args, kwargs = mock_session.get.call_args
        url = args[0]
        assert url.host == "1.2.3.4"
        assert url.port == 8081
        assert url.path == "/healthcheck"
        assert kwargs["headers"]["Authorization"] == "Bearer secret_key"


async def test_async_check_daemon_status_invalid_payload(hass: HomeAssistant) -> None:
    """Test health check handles invalid payload gracefully."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.text = AsyncMock(return_value="error")
        mock_session.get.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response)
        )
        mock_session_getter.return_value = mock_session

        result = await async_check_daemon_status(hass, "1.2.3.4", 8081, "key")
        assert result is False


async def test_async_check_daemon_status_failure(hass: HomeAssistant) -> None:
    """Test health check handles failures gracefully."""
    with patch(
        "custom_components.grubstation.daemon.async_get_clientsession"
    ) as mock_session_getter:
        mock_session = MagicMock()
        mock_session.get.side_effect = TimeoutError()
        mock_session_getter.return_value = mock_session

        result = await async_check_daemon_status(hass, "1.2.3.4", 8081, "key")
        assert result is False

"""Tests for the GrubStationCoordinator."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.grubstation.coordinator import GrubStationCoordinator, _async_ping_host
from custom_components.grubstation.data import RemoteHost


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        agent_port=8081,
        agent_token="secret",
    )


@pytest.fixture
def mock_manager():
    """Return a mock manager."""
    manager = MagicMock()
    manager.async_log_activity = MagicMock()
    return manager


async def test_coordinator_update_success(hass, mock_host, mock_manager):
    """Test successful coordinator update."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=True,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
            return_value={
                "os": "linux",
                "service_manager": "systemd",
                "version": "1.0.0",
            },
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_called_once_with(hass, "1.2.3.4", 8081, "secret")

        assert mock_host.is_powered_on is True
        assert mock_host.is_agent_accessible is True
        assert mock_host.last_agent_accessible is not None
        assert mock_host.os == "linux"
        assert mock_host.agent_service_manager == "systemd"
        assert mock_host.agent_version == "1.0.0"


async def test_coordinator_update_no_ping(hass, mock_host, mock_manager):
    """Test coordinator update when host is not pingable."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=False,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_not_called()

        assert mock_host.is_powered_on is False
        assert mock_host.is_agent_accessible is False


async def test_coordinator_update_no_agent(hass, mock_host, mock_manager):
    """Test coordinator update when agent check fails."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=True,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
            return_value=None,
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_called_once()

        assert mock_host.is_powered_on is True
        assert mock_host.is_agent_accessible is False


async def test_coordinator_update_no_address(hass, mock_manager):
    """Test coordinator update with no address."""
    host = RemoteHost(mac="00:11:22:33:44:55")
    coordinator = GrubStationCoordinator(hass, mock_manager, host)

    await coordinator._async_update_data()
    assert host.is_powered_on is False
    assert host.is_agent_accessible is False


async def test_coordinator_update_missing_agent_config(hass, mock_manager):
    """Test coordinator update when host is alive but agent config is missing."""
    # Host has address but no port/token
    host = RemoteHost(mac="00:11:22:33:44:55", address="1.2.3.4")
    coordinator = GrubStationCoordinator(hass, mock_manager, host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=True,
        ),
        patch("custom_components.grubstation.coordinator.LOGGER.debug") as mock_log,
    ):
        await coordinator._async_update_data()

        mock_log.assert_any_call("Skipping agent check for %s: missing port or token", "00:11:22:33:44:55")
        assert host.is_powered_on is True
        assert host.is_agent_accessible is False


async def test_coordinator_ping_exception_logging(hass):
    """Test coordinator debug logging when ping raises an exception."""
    with (
        patch(
            "custom_components.grubstation.coordinator.async_ping",
            side_effect=Exception("Ping Failure"),
        ),
        patch("custom_components.grubstation.coordinator.LOGGER.debug") as mock_log,
    ):
        result = await _async_ping_host("1.2.3.4")
        assert result is False
        # Use more flexible check
        found = False
        for call_args in mock_log.call_args_list:
            # call_args is (args, kwargs). args[0] is the format string.
            if call_args[0][0] == "Ping failed for %s: %s" and call_args[0][1] == "1.2.3.4":
                found = True
                break
        assert found

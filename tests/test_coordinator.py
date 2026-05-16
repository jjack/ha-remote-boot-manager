"""Tests for the GrubStationCoordinator."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.grubstation.const import API_KEY_OS, API_KEY_SERVICE_MANAGER, API_KEY_STATUS, API_KEY_VERSION
from custom_components.grubstation.coordinator import GrubStationCoordinator, async_check_tcp_reachability
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
            "custom_components.grubstation.coordinator.async_check_tcp_reachability",
            return_value=True,
        ) as mock_reachability,
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
            return_value={
                API_KEY_STATUS: "ok",
                API_KEY_OS: "linux",
                API_KEY_SERVICE_MANAGER: "systemd",
                API_KEY_VERSION: "1.0.0",
            },
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_reachability.assert_called_once_with("1.2.3.4", 8081)
        mock_agent.assert_called_once_with(hass, "1.2.3.4", 8081, "secret")

        assert mock_host.is_powered_on is True
        assert mock_host.is_agent_accessible is True
        assert mock_host.last_agent_accessible is not None
        assert mock_host.os == "linux"
        assert mock_host.agent_service_manager == "systemd"
        assert mock_host.agent_version == "1.0.0"


async def test_coordinator_update_no_reachability(hass, mock_host, mock_manager):
    """Test coordinator update when host is not reachable."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator.async_check_tcp_reachability",
            return_value=False,
        ) as mock_reachability,
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_reachability.assert_called_once_with("1.2.3.4", 8081)
        mock_agent.assert_not_called()

        assert mock_host.is_powered_on is False
        assert mock_host.is_agent_accessible is False


async def test_coordinator_update_agent_exception(hass, mock_host, mock_manager, caplog):
    """Test coordinator update when agent check fails and logs warning."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator.async_check_tcp_reachability",
            return_value=True,
        ),
        patch(
            "custom_components.grubstation.coordinator.async_get_agent_status",
            side_effect=Exception("Test Exception"),
        ),
    ):
        await coordinator._async_update_data()
        assert "Agent unhealthy for" in caplog.text


async def test_coordinator_update_no_address(hass, mock_manager):
    """Test coordinator update with no address."""
    host = RemoteHost(mac="00:11:22:33:44:55")
    coordinator = GrubStationCoordinator(hass, mock_manager, host)

    await coordinator._async_update_data()
    assert host.is_powered_on is False
    assert host.is_agent_accessible is False


async def test_coordinator_reachability_timeout_logging(hass):
    """Test coordinator debug logging when TCP check raises a TimeoutError."""
    with patch(
        "asyncio.open_connection",
        side_effect=TimeoutError("Connect Timeout"),
    ):
        result = await async_check_tcp_reachability("1.2.3.4", 8081)
        assert result is False


async def test_async_update_host_data(hass, mock_host, mock_manager):
    """Test updating host data from payload."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)
    payload = {
        "address": "new.address",
        "boot_options": ["a", "b"],
    }

    await coordinator.async_update_host_data(payload)

    assert mock_host.address == "new.address"
    assert mock_host.boot_options == ["a", "b"]
    mock_manager.save.assert_called_once()


async def test_async_set_next_boot_option(hass, mock_host, mock_manager):
    """Test setting next boot option."""
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)

    await coordinator.async_set_next_boot_option("option_a")

    assert mock_host.next_boot_option == "option_a"
    mock_manager.save.assert_called_once()


async def test_async_consume_next_boot_option(hass, mock_host, mock_manager):
    """Test consuming next boot option."""
    mock_host.next_boot_option = "option_b"
    coordinator = GrubStationCoordinator(hass, mock_manager, mock_host)
    coordinator.async_log_activity = MagicMock()

    consumed = await coordinator.async_consume_next_boot_option()

    assert consumed == "option_b"
    assert mock_host.next_boot_option == "(none)"
    mock_manager.save.assert_called_once()
    coordinator.async_log_activity.assert_called_once()

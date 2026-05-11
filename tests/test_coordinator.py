"""Tests for the GrubStationCoordinator."""

from unittest.mock import patch

import pytest

from custom_components.grubstation.coordinator import GrubStationCoordinator
from custom_components.grubstation.data import RemoteHost


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        agent_port=8081,
        api_key="secret",
    )


async def test_coordinator_update_success(hass, mock_host):
    """Test successful coordinator update."""
    coordinator = GrubStationCoordinator(hass, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=True,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_check_agent_status",
            return_value=True,
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_called_once_with(hass, "1.2.3.4", 8081, "secret")

        assert mock_host.is_powered_on is True
        assert mock_host.is_agent_accessible is True
        assert mock_host.last_agent_accessible is not None


async def test_coordinator_update_no_ping(hass, mock_host):
    """Test coordinator update when host is not pingable."""
    coordinator = GrubStationCoordinator(hass, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=False,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_check_agent_status",
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_not_called()

        assert mock_host.is_powered_on is False
        assert mock_host.is_agent_accessible is False


async def test_coordinator_update_no_agent(hass, mock_host):
    """Test coordinator update when agent check fails."""
    coordinator = GrubStationCoordinator(hass, mock_host)

    with (
        patch(
            "custom_components.grubstation.coordinator._async_ping_host",
            return_value=True,
        ) as mock_ping,
        patch(
            "custom_components.grubstation.coordinator.async_check_agent_status",
            return_value=False,
        ) as mock_agent,
    ):
        await coordinator._async_update_data()

        mock_ping.assert_called_once_with("1.2.3.4")
        mock_agent.assert_called_once()

        assert mock_host.is_powered_on is True
        assert mock_host.is_agent_accessible is False


async def test_coordinator_update_no_address(hass):
    """Test coordinator update with no address."""
    host = RemoteHost(mac="00:11:22:33:44:55")
    coordinator = GrubStationCoordinator(hass, host)

    await coordinator._async_update_data()
    assert host.is_powered_on is False
    assert host.is_agent_accessible is False

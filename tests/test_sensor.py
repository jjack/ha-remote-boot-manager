"""Tests for the GrubStation sensor platform."""

from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from custom_components.grubstation.const import SIGNAL_HOST_REMOVED, SIGNAL_HOST_UPDATED, SIGNAL_NEW_HOST
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.sensor import GrubStationManagerSensor, async_setup_entry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


@pytest.fixture
def mock_host_with_agent():
    """Return a mock RemoteHost with agent config."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="192.168.1.100",
        agent_port=8080,
        agent_token="test-key",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
    )


@pytest.fixture
def mock_host_without_agent():
    """Return a mock RemoteHost without agent config."""
    return RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
        is_agent_accessible=False,
        last_agent_accessible=None,
    )


@pytest.fixture
def mock_coordinator(mock_host_with_agent):
    """Return a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_host_with_agent
    coordinator.host = mock_host_with_agent
    return coordinator


async def test_sensor_properties(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor properties."""
    sensor = GrubStationManagerSensor(mock_coordinator)

    assert sensor.unique_id == "00:11:22:33:44:55_last_agent_accessible"
    assert sensor.name == "Last Successful Agent Healthcheck"
    assert sensor.icon == "mdi:heart-pulse"
    assert sensor.should_poll is False
    assert sensor.has_entity_name is True


async def test_sensor_native_value(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor native value."""
    sensor = GrubStationManagerSensor(mock_coordinator)

    # Should return the timestamp when agent is accessible
    assert sensor.native_value == "2023-01-01T12:00:00+00:00"

    # Should return None when timestamp is not set
    mock_coordinator.data.last_agent_accessible = None
    assert sensor.native_value is None


async def test_sensor_device_info(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor device info is set."""
    sensor = GrubStationManagerSensor(mock_coordinator)

    # Check that device info is properly configured
    # (Home Assistant converts DeviceInfo to dict)
    device_info = sensor._attr_device_info
    assert device_info is not None


async def test_async_setup_entry_with_agent_hosts(hass: HomeAssistant):
    """Test setting up the sensor platform with hosts that have agents."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()

    # Create hosts with and without agent config
    host_with_agent = RemoteHost(
        mac="00:11:22:33:44:55",
        address="192.168.1.100",
        agent_port=8080,
        agent_token="test-key",
    )
    coordinator_with_agent = MagicMock()
    coordinator_with_agent.data = host_with_agent
    coordinator_with_agent.host = host_with_agent

    host_without_agent = RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )
    coordinator_without_agent = MagicMock()
    coordinator_without_agent.data = host_without_agent
    coordinator_without_agent.host = host_without_agent

    mock_manager.hosts = {
        "00:11:22:33:44:55": host_with_agent,
        "AA:BB:CC:DD:EE:FF": host_without_agent,
    }
    mock_manager.coordinators = {
        "00:11:22:33:44:55": coordinator_with_agent,
        "AA:BB:CC:DD:EE:FF": coordinator_without_agent,
    }
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should only add sensor for host with agent config
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerSensor)
        assert added_entities[0].host.mac == "00:11:22:33:44:55"

        # Should connect to the new host signals
        assert mock_dispatch.call_count == 3
        mock_dispatch.assert_any_call(hass, SIGNAL_NEW_HOST, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_UPDATED, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_REMOVED, mock.ANY)
        assert mock_entry.async_on_unload.call_count == 3


async def test_async_setup_entry_no_agent_hosts(hass: HomeAssistant):
    """Test setting up the sensor platform with no agent hosts."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()

    # Only add hosts without agent config
    host_without_agent = RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )
    coordinator_without_agent = MagicMock()
    coordinator_without_agent.data = host_without_agent
    coordinator_without_agent.host = host_without_agent

    mock_manager.hosts = {"AA:BB:CC:DD:EE:FF": host_without_agent}
    mock_manager.coordinators = {"AA:BB:CC:DD:EE:FF": coordinator_without_agent}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should not add any sensors since host has no agent config
        mock_add_entities.assert_not_called()

        # Should still connect to the new host signals
        assert mock_dispatch.call_count == 3
        mock_dispatch.assert_any_call(hass, SIGNAL_NEW_HOST, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_UPDATED, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_REMOVED, mock.ANY)
        assert mock_entry.async_on_unload.call_count == 3


async def test_async_setup_entry_signal_callback_with_agent(hass: HomeAssistant):
    """Test signal callback adds sensor for new host with agent."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Get the callback function for SIGNAL_NEW_HOST
        callback = next(call[0][2] for call in mock_dispatch.call_args_list if call[0][1] == SIGNAL_NEW_HOST)

        # Add a new host with agent config
        new_mac = "00:11:22:33:44:55"
        new_host = RemoteHost(
            mac=new_mac,
            address="192.168.1.100",
            agent_port=8080,
            agent_token="test-key",
        )
        new_coordinator = MagicMock()
        new_coordinator.data = new_host
        new_coordinator.host = new_host
        mock_manager.hosts[new_mac] = new_host
        mock_manager.coordinators[new_mac] = new_coordinator
        mock_add_entities.reset_mock()

        # Call the signal callback
        callback(new_mac)

        # Should add the sensor
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerSensor)
        assert added_entities[0].host.mac == new_mac


async def test_async_setup_entry_signal_callback_without_agent(hass: HomeAssistant):
    """Test signal callback does not add sensor for new host without agent."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Get the callback function for SIGNAL_NEW_HOST
        callback = next(call[0][2] for call in mock_dispatch.call_args_list if call[0][1] == SIGNAL_NEW_HOST)

        # Add a new host without agent config
        new_mac = "AA:BB:CC:DD:EE:FF"
        new_host = RemoteHost(
            mac=new_mac,
            broadcast_address="192.168.1.255",
            broadcast_port=9,
        )
        new_coordinator = MagicMock()
        new_coordinator.data = new_host
        new_coordinator.host = new_host
        mock_manager.hosts[new_mac] = new_host
        mock_manager.coordinators[new_mac] = new_coordinator
        mock_add_entities.reset_mock()

        # Call the signal callback
        callback(new_mac)

        # Should not call add_entities since host has no agent config
        mock_add_entities.assert_not_called()


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test signal callback does not add entity if coordinator is missing."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = []
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager
    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)
        callback = next(call[0][2] for call in mock_dispatch.call_args_list if call[0][1] == SIGNAL_NEW_HOST)
        callback("00:AA:BB:CC:DD:EE")
        assert mock_add_entities.call_count == 0

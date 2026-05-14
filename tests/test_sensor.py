"""Tests for the GrubStation sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.grubstation.const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
    ATTR_RECENT_ACTIVITY,
    SIGNAL_NEW_HOST,
)
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.sensor import GrubStationManagerSensor, async_setup_entry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        agent_port=8080,
        agent_token="secret",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
        os="linux",
        agent_service_manager="systemd",
        agent_version="1.0.0",
    )


@pytest.fixture
def mock_coordinator(mock_host):
    """Return a mock coordinator."""
    coordinator = MagicMock()
    coordinator.host = mock_host
    return coordinator


async def test_sensor_properties(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor properties."""
    sensor = GrubStationManagerSensor(mock_coordinator)

    assert sensor.unique_id == "00:11:22:33:44:55_last_agent_accessible"
    assert sensor.translation_key == "last_agent_accessible"
    assert sensor.should_poll is False
    assert sensor.has_entity_name is True


async def test_sensor_native_value(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor native value."""
    sensor = GrubStationManagerSensor(mock_coordinator)
    assert sensor.native_value == "2023-01-01T12:00:00+00:00"


async def test_sensor_device_info(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor device info."""
    sensor = GrubStationManagerSensor(mock_coordinator)
    # (Home Assistant converts DeviceInfo to dict)
    device_info = sensor._attr_device_info
    assert device_info is not None


async def test_sensor_extra_state_attributes(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test sensor extra state attributes."""
    mock_coordinator.host.os = "linux"
    mock_coordinator.host.agent_service_manager = "systemd"
    mock_coordinator.host.agent_version = "1.0.0"
    mock_coordinator.host.agent_status = "ok"
    mock_coordinator.host.activity_history = ["Activity 1"]

    sensor = GrubStationManagerSensor(mock_coordinator)

    assert sensor.extra_state_attributes == {
        ATTR_AGENT_STATUS: "ok",
        ATTR_HOST_OS: "linux",
        ATTR_AGENT_SERVICE_MANAGER: "systemd",
        ATTR_AGENT_VERSION: "1.0.0",
        ATTR_RECENT_ACTIVITY: ["Activity 1"],
    }


async def test_async_setup_entry_with_agent_hosts(hass: HomeAssistant):
    """Test setting up the sensor platform with hosts that have agents."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_host = RemoteHost(
        mac=mac,
        address="1.2.3.4",
        agent_port=8080,
        agent_token="secret",
    )
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host
    mock_manager.hosts = {mac: mock_host}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect"):
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should add the healthcheck sensor for the host
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerSensor)


async def test_async_setup_entry_no_agent_hosts(hass: HomeAssistant):
    """Test that sensors are not added for hosts without agent config."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_host = RemoteHost(mac=mac)  # No agent details
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host
    mock_manager.hosts = {mac: mock_host}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect"):
        await async_setup_entry(hass, mock_entry, mock_add_entities)
        mock_add_entities.assert_not_called()


async def test_async_setup_entry_signal_callback_with_agent(hass: HomeAssistant):
    """Test signal callback adds sensors when agent is configured."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager
    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.sensor.async_dispatcher_connect") as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Get the callback for SIGNAL_NEW_HOST
        callback = next(call[0][2] for call in mock_dispatch.call_args_list if call[0][1] == SIGNAL_NEW_HOST)

        new_mac = "AA:BB:CC:DD:EE:FF"
        new_host = RemoteHost(
            mac=new_mac,
            address="4.5.6.7",
            agent_port=8080,
            agent_token="secret",
        )
        new_coordinator = MagicMock()
        new_coordinator.host = new_host
        mock_manager.hosts[new_mac] = new_host
        mock_manager.coordinators[new_mac] = new_coordinator

        callback(new_mac)

        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1


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

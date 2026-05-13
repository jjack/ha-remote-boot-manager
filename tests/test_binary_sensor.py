"""Tests for the GrubStation binary sensor platform."""

from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.grubstation.binary_sensor import (
    GrubStationManagerBinarySensor,
    async_setup_entry,
)
from custom_components.grubstation.const import (
    SIGNAL_HOST_REMOVED,
    SIGNAL_HOST_UPDATED,
    SIGNAL_NEW_HOST,
)
from custom_components.grubstation.data import RemoteHost


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        daemon_port=8080,
        daemon_token="secret",  # noqa: S106
        is_daemon_accessible=True,
        last_daemon_accessible="2023-01-01T12:00:00+00:00",
    )


@pytest.fixture
def mock_coordinator(mock_host):
    """Return a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_host
    coordinator.host = mock_host
    return coordinator


async def test_binary_sensor_properties(
    hass: HomeAssistant, mock_coordinator: MagicMock
):
    """Test binary sensor properties."""
    sensor = GrubStationManagerBinarySensor(mock_coordinator)

    assert sensor.unique_id == "00:11:22:33:44:55_health_status"
    assert sensor.name == "Daemon Status"
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.should_poll is False

    # The entity doesn't have an entity_id assigned yet, so we just check state properties
    assert sensor.is_on is True
    assert sensor.extra_state_attributes == {
        "last_daemon_accessible": "2023-01-01T12:00:00+00:00"
    }

    # Test state change
    mock_coordinator.data.is_daemon_accessible = False
    assert sensor.is_on is False


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test setting up the binary sensor platform."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_manager.hosts = {mac: mock_coordinator.data}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grubstation.binary_sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should add entities for existing hosts
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerBinarySensor)
        assert added_entities[0].host.mac == mac

        assert mock_dispatch.call_count == 3
        mock_dispatch.assert_any_call(hass, SIGNAL_NEW_HOST, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_UPDATED, mock.ANY)
        mock_dispatch.assert_any_call(hass, SIGNAL_HOST_REMOVED, mock.ANY)
        assert mock_entry.async_on_unload.call_count == 3

        # Test signal callback with daemon
        callback = next(
            call[0][2]
            for call in mock_dispatch.call_args_list
            if call[0][1] == SIGNAL_NEW_HOST
        )
        new_mac_with_daemon = "AA:BB:CC:DD:EE:FF"
        new_host_with_daemon = RemoteHost(
            mac=new_mac_with_daemon,
            address="4.5.6.7",
            daemon_port=8080,
            daemon_token="secret",  # noqa: S106
        )
        new_coordinator_with_daemon = MagicMock()
        new_coordinator_with_daemon.data = new_host_with_daemon
        new_coordinator_with_daemon.host = new_host_with_daemon
        mock_manager.hosts[new_mac_with_daemon] = new_host_with_daemon
        mock_manager.coordinators[new_mac_with_daemon] = new_coordinator_with_daemon
        mock_add_entities.reset_mock()
        callback(new_mac_with_daemon)

        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerBinarySensor)
        assert added_entities[0].host.mac == new_mac_with_daemon

        # Test signal callback without daemon
        new_mac_no_daemon = "11:22:33:44:55:66"
        new_host_no_daemon = RemoteHost(mac=new_mac_no_daemon)
        new_coordinator_no_daemon = MagicMock()
        new_coordinator_no_daemon.data = new_host_no_daemon
        new_coordinator_no_daemon.host = new_host_no_daemon
        mock_manager.hosts[new_mac_no_daemon] = new_host_no_daemon
        mock_manager.coordinators[new_mac_no_daemon] = new_coordinator_no_daemon
        mock_add_entities.reset_mock()
        callback(new_mac_no_daemon)

        mock_add_entities.assert_not_called()


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test signal callback does not add entity if coordinator is missing."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = []
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager
    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grubstation.binary_sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)
        callback = next(
            call[0][2]
            for call in mock_dispatch.call_args_list
            if call[0][1] == SIGNAL_NEW_HOST
        )
        callback("00:AA:BB:CC:DD:EE")
        assert mock_add_entities.call_count == 0


async def test_async_setup_entry_no_daemon(hass: HomeAssistant):
    """Test that sensors are not added for hosts without daemon config."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_host = RemoteHost(mac=mac)  # No daemon details
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_host
    mock_coordinator.host = mock_host
    mock_manager.hosts = {mac: mock_host}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch("custom_components.grubstation.binary_sensor.async_dispatcher_connect"):
        await async_setup_entry(hass, mock_entry, mock_add_entities)
        mock_add_entities.assert_not_called()

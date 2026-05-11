"""Tests for the GrubStation binary sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.grubstation.binary_sensor import (
    GrubStationManagerBinarySensor,
    async_setup_entry,
)
from custom_components.grubstation.const import SIGNAL_NEW_HOST
from custom_components.grubstation.data import RemoteHost


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
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
    assert sensor.name == "Agent Status"
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.should_poll is False

    # The entity doesn't have an entity_id assigned yet, so we just check state properties
    assert sensor.is_on is True
    assert sensor.extra_state_attributes == {
        "last_agent_accessible": "2023-01-01T12:00:00+00:00"
    }

    # Test state change
    mock_coordinator.data.is_agent_accessible = False
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

        # Should connect to the new host signal
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][1] == SIGNAL_NEW_HOST

        # Test signal callback
        callback = mock_dispatch.call_args[0][2]
        new_mac = "AA:BB:CC:DD:EE:FF"
        new_host = RemoteHost(mac=new_mac)
        new_coordinator = MagicMock()
        new_coordinator.data = new_host
        new_coordinator.host = new_host
        mock_manager.hosts[new_mac] = new_host
        mock_manager.coordinators[new_mac] = new_coordinator
        mock_add_entities.reset_mock()
        callback(new_mac)

        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubStationManagerBinarySensor)
        assert added_entities[0].host.mac == new_mac

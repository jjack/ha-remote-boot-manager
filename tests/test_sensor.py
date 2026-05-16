"""Tests for the GrubStation sensor platform."""

from unittest.mock import MagicMock

import pytest

from custom_components.grubstation.const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
)
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.sensor import SENSOR_DESCRIPTIONS, GrubStationManagerSensor, async_setup_entry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        agent_port=8081,
        agent_token="test-token",
    )
    host.last_agent_accessible = "2023-01-01T12:00:00+00:00"
    host.os = "linux"
    host.agent_service_manager = "systemd"
    host.agent_version = "1.0.0"
    host.agent_status = "ok"
    return host


@pytest.fixture
def mock_coordinator(mock_host):
    """Return a mock DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_host
    coordinator.host = mock_host
    return coordinator


async def test_sensor_properties(mock_coordinator):
    """Test the properties of the sensor."""
    description = SENSOR_DESCRIPTIONS[0]
    sensor = GrubStationManagerSensor(mock_coordinator, description)

    assert sensor.unique_id == "00:11:22:33:44:55_last_agent_accessible"
    assert sensor.native_value == "2023-01-01T12:00:00+00:00"


async def test_sensor_extra_state_attributes(mock_coordinator):
    """Test sensor extra state attributes."""
    description = SENSOR_DESCRIPTIONS[0]
    sensor = GrubStationManagerSensor(mock_coordinator, description)

    assert sensor.extra_state_attributes == {
        ATTR_AGENT_STATUS: "ok",
        ATTR_HOST_OS: "linux",
        ATTR_AGENT_SERVICE_MANAGER: "systemd",
        ATTR_AGENT_VERSION: "1.0.0",
    }


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test setting up the sensor platform."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_MAC: "00:11:22:33:44:55"}
    mock_entry.runtime_data = mock_coordinator

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    await async_setup_entry(hass, mock_entry, mock_add_entities)
    mock_add_entities.assert_called_once()


async def test_async_setup_entry_global(hass: HomeAssistant):
    """Test that setup does nothing for global entry."""
    mock_entry = MagicMock()
    mock_entry.data = {}

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    await async_setup_entry(hass, mock_entry, mock_add_entities)
    mock_add_entities.assert_not_called()


async def test_async_setup_entry_no_agent_hosts(hass: HomeAssistant):
    """Test that sensors are not added for hosts without agent config."""
    mock_host = RemoteHost(mac="00:11:22:33:44:55")  # No agent details
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host

    mock_entry = MagicMock()
    mock_entry.data = {CONF_MAC: "00:11:22:33:44:55"}
    mock_entry.runtime_data = mock_coordinator

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    await async_setup_entry(hass, mock_entry, mock_add_entities)
    mock_add_entities.assert_not_called()

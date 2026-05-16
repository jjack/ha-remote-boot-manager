"""Tests for the GrubStation binary sensor platform."""

from unittest.mock import MagicMock

import pytest

from custom_components.grubstation.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    GrubStationManagerBinarySensor,
    async_setup_entry,
)
from custom_components.grubstation.const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
    ATTR_LAST_AGENT_ACCESSIBLE,
)
from custom_components.grubstation.data import RemoteHost
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_MAC, EntityCategory
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
    host.is_agent_accessible = True
    host.last_agent_accessible = "2023-01-01T12:00:00+00:00"
    host.os = "linux"
    host.agent_service_manager = "systemd"
    host.agent_version = "1.0.0"
    return host


@pytest.fixture
def mock_coordinator(mock_host):
    """Return a mock DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_host
    coordinator.host = mock_host
    return coordinator


async def test_binary_sensor_properties(mock_coordinator):
    """Test the properties of the binary sensor."""
    description = BINARY_SENSOR_DESCRIPTIONS[0]
    sensor = GrubStationManagerBinarySensor(mock_coordinator, description)

    assert sensor.unique_id == "00:11:22:33:44:55_health_status"
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.should_poll is False

    # The entity doesn't have an entity_id assigned yet, so we just check state properties
    assert sensor.is_on is True
    assert sensor.extra_state_attributes == {
        ATTR_LAST_AGENT_ACCESSIBLE: "2023-01-01T12:00:00+00:00",
        ATTR_HOST_OS: "linux",
        ATTR_AGENT_SERVICE_MANAGER: "systemd",
        ATTR_AGENT_VERSION: "1.0.0",
        ATTR_AGENT_STATUS: None,
    }


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator: MagicMock):
    """Test setting up the binary sensor platform."""
    # Create a per-host entry
    mock_entry = MagicMock()
    mock_entry.data = {CONF_MAC: "00:11:22:33:44:55"}
    mock_entry.runtime_data = mock_coordinator

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    await async_setup_entry(hass, mock_entry, mock_add_entities)

    # Should add entities for the host in entry
    mock_add_entities.assert_called_once()
    added_entities = mock_add_entities.call_args[0][0]
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], GrubStationManagerBinarySensor)
    assert added_entities[0].host.mac == "00:11:22:33:44:55"


async def test_async_setup_entry_global(hass: HomeAssistant):
    """Test that setup does nothing for the global entry."""
    mock_entry = MagicMock()
    mock_entry.data = {}  # Global entry has no MAC

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    await async_setup_entry(hass, mock_entry, mock_add_entities)
    mock_add_entities.assert_not_called()


async def test_async_setup_entry_no_agent(hass: HomeAssistant):
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

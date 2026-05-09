"""Tests for the Grub OS Selector binary sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.grub_os_selector.binary_sensor import (
    GrubOSSelectManagerBinarySensor,
    async_setup_entry,
)
from custom_components.grub_os_selector.const import DOMAIN, SIGNAL_NEW_HOST
from custom_components.grub_os_selector.data import RemoteHost


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        name="test-host",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
    )


async def test_binary_sensor_properties(hass: HomeAssistant, mock_host: RemoteHost):
    """Test binary sensor properties."""
    sensor = GrubOSSelectManagerBinarySensor(hass, mock_host)

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
    mock_host.is_agent_accessible = False
    assert sensor.is_on is False


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setting up the binary sensor platform."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(mac="00:11:22:33:44:55", name="host1")
    }
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grub_os_selector.binary_sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should add entities for existing hosts
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubOSSelectManagerBinarySensor)
        assert added_entities[0].host.mac == "00:11:22:33:44:55"

        # Should connect to the new host signal
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][1] == SIGNAL_NEW_HOST

        # Test signal callback
        callback = mock_dispatch.call_args[0][2]
        mock_manager.hosts["AA:BB:CC:DD:EE:FF"] = RemoteHost(
            mac="AA:BB:CC:DD:EE:FF", name="host2"
        )
        mock_add_entities.reset_mock()
        callback("AA:BB:CC:DD:EE:FF")

        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubOSSelectManagerBinarySensor)
        assert added_entities[0].host.mac == "AA:BB:CC:DD:EE:FF"


async def test_async_added_to_hass(hass: HomeAssistant, mock_host: RemoteHost):
    """Test entity added to hass connects to dispatcher."""
    sensor = GrubOSSelectManagerBinarySensor(hass, mock_host)
    sensor.hass = hass

    with (
        patch(
            "custom_components.grub_os_selector.binary_sensor.async_dispatcher_connect"
        ) as mock_dispatch,
        patch.object(sensor, "async_on_remove") as mock_on_remove,
    ):
        await sensor.async_added_to_hass()

        mock_dispatch.assert_called_once_with(
            hass,
            f"{DOMAIN}_update_00:11:22:33:44:55",
            sensor.async_write_ha_state,
        )
        mock_on_remove.assert_called_once()

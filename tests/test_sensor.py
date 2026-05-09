"""Tests for the Grub OS Selector sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.grub_os_selector.const import DOMAIN, SIGNAL_NEW_HOST
from custom_components.grub_os_selector.data import RemoteHost
from custom_components.grub_os_selector.sensor import (
    GrubOSSelectManagerSensor,
    async_setup_entry,
)


@pytest.fixture
def mock_host_with_agent():
    """Return a mock RemoteHost with agent config."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        name="test-host",
        address="192.168.1.100",
        agent_port=8080,
        api_key="test-key",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
    )


@pytest.fixture
def mock_host_without_agent():
    """Return a mock RemoteHost without agent config."""
    return RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        name="wol-only-host",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
        is_agent_accessible=False,
        last_agent_accessible=None,
    )


async def test_sensor_properties(hass: HomeAssistant, mock_host_with_agent: RemoteHost):
    """Test sensor properties."""
    sensor = GrubOSSelectManagerSensor(hass, mock_host_with_agent)

    assert sensor.unique_id == "00:11:22:33:44:55_last_agent_accessible"
    assert sensor.name == "Last Succesful Agent Healthcheck"
    assert sensor.icon == "mdi:heart-pulse"
    assert sensor.should_poll is False
    assert sensor.has_entity_name is True


async def test_sensor_native_value(
    hass: HomeAssistant, mock_host_with_agent: RemoteHost
):
    """Test sensor native value."""
    sensor = GrubOSSelectManagerSensor(hass, mock_host_with_agent)

    # Should return the timestamp when agent is accessible
    assert sensor.native_value == "2023-01-01T12:00:00+00:00"

    # Should return None when timestamp is not set
    mock_host_with_agent.last_agent_accessible = None
    assert sensor.native_value is None


async def test_sensor_device_info(
    hass: HomeAssistant, mock_host_with_agent: RemoteHost
):
    """Test sensor device info is set."""
    sensor = GrubOSSelectManagerSensor(hass, mock_host_with_agent)

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
        name="host1",
        address="192.168.1.100",
        agent_port=8080,
        api_key="test-key",
    )
    host_without_agent = RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        name="host2",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )

    mock_manager.hosts = {
        "00:11:22:33:44:55": host_with_agent,
        "AA:BB:CC:DD:EE:FF": host_without_agent,
    }
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grub_os_selector.sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should only add sensor for host with agent config
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubOSSelectManagerSensor)
        assert added_entities[0].host.mac == "00:11:22:33:44:55"

        # Should connect to the new host signal
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][1] == SIGNAL_NEW_HOST


async def test_async_setup_entry_no_agent_hosts(hass: HomeAssistant):
    """Test setting up the sensor platform with no agent hosts."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()

    # Only add hosts without agent config
    host_without_agent = RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        name="host1",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )
    mock_manager.hosts = {"AA:BB:CC:DD:EE:FF": host_without_agent}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grub_os_selector.sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Should not add any sensors since host has no agent config
        mock_add_entities.assert_not_called()

        # Should still connect to the new host signal
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][1] == SIGNAL_NEW_HOST


async def test_async_setup_entry_signal_callback_with_agent(hass: HomeAssistant):
    """Test signal callback adds sensor for new host with agent."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grub_os_selector.sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Get the callback function
        callback = mock_dispatch.call_args[0][2]

        # Add a new host with agent config
        new_host = RemoteHost(
            mac="00:11:22:33:44:55",
            name="new-host",
            address="192.168.1.100",
            agent_port=8080,
            api_key="test-key",
        )
        mock_manager.hosts["00:11:22:33:44:55"] = new_host
        mock_add_entities.reset_mock()

        # Call the signal callback
        callback("00:11:22:33:44:55")

        # Should add the sensor
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], GrubOSSelectManagerSensor)
        assert added_entities[0].host.mac == "00:11:22:33:44:55"


async def test_async_setup_entry_signal_callback_without_agent(hass: HomeAssistant):
    """Test signal callback does not add sensor for new host without agent."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_entry.runtime_data = mock_manager

    mock_add_entities = MagicMock(spec=AddEntitiesCallback)

    with patch(
        "custom_components.grub_os_selector.sensor.async_dispatcher_connect"
    ) as mock_dispatch:
        await async_setup_entry(hass, mock_entry, mock_add_entities)

        # Get the callback function
        callback = mock_dispatch.call_args[0][2]

        # Add a new host without agent config
        new_host = RemoteHost(
            mac="AA:BB:CC:DD:EE:FF",
            name="wol-host",
            broadcast_address="192.168.1.255",
            broadcast_port=9,
        )
        mock_manager.hosts["AA:BB:CC:DD:EE:FF"] = new_host
        mock_add_entities.reset_mock()

        # Call the signal callback
        callback("AA:BB:CC:DD:EE:FF")

        # Should not call add_entities since host has no agent config
        mock_add_entities.assert_not_called()


async def test_async_added_to_hass(hass: HomeAssistant, mock_host_with_agent):
    """Test entity added to hass connects to dispatcher."""
    sensor = GrubOSSelectManagerSensor(hass, mock_host_with_agent)
    sensor.hass = hass

    with (
        patch(
            "custom_components.grub_os_selector.sensor.async_dispatcher_connect"
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

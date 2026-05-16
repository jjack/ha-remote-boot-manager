"""Tests for the GrubStation switch platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.switch import GrubStationManagerSwitch, async_setup_entry
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_host():
    """Return a mock RemoteHost."""
    return RemoteHost(
        mac="00:11:22:33:44:55",
        address="1.2.3.4",
        agent_port=8081,
        agent_token="test-token",
    )


@pytest.fixture
def mock_coordinator(mock_host):
    """Return a mock DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_host
    coordinator.host = mock_host
    coordinator.async_log_activity = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_switch_properties(hass, mock_coordinator):
    """Test the properties of the switch."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    assert switch.unique_id == "00:11:22:33:44:55_power_switch"
    assert switch.device_class == SwitchDeviceClass.SWITCH
    assert switch.is_on is False
    assert switch.assumed_state is False


async def test_async_turn_on(hass, mock_coordinator):
    """Test turning the switch on (Wake-on-LAN)."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock) as mock_job,
        patch.object(hass, "async_create_background_task", return_value=MagicMock()) as mock_task,
        patch("wakeonlan.send_magic_packet"),
    ):
        await switch.async_turn_on()
        mock_job.assert_called_once()
        mock_task.assert_called_once()
        mock_task.call_args.args[0].close()  # Close unawaited coroutine
        mock_coordinator.async_log_activity.assert_called_with("Sending Wake-on-LAN command")


async def test_async_turn_off_agent(hass, mock_coordinator):
    """Test turning the switch off via agent."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch.object(hass, "async_create_background_task", return_value=MagicMock()) as mock_task,
        patch(
            "custom_components.grubstation.switch.async_send_turn_off_command", new_callable=AsyncMock
        ) as mock_send_off,
    ):
        await switch.async_turn_off()
        mock_send_off.assert_called_once()
        mock_task.assert_called_once()
        mock_task.call_args.args[0].close()  # Close unawaited coroutine
        mock_coordinator.async_log_activity.assert_called_with("Sending shutdown command to agent")


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator):
    """Test setting up the switch platform."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_MAC: "00:11:22:33:44:55"}
    mock_entry.runtime_data = mock_coordinator

    async_add_entities = MagicMock()

    await async_setup_entry(hass, mock_entry, async_add_entities)

    assert async_add_entities.call_count == 1
    added_entities = async_add_entities.call_args[0][0]
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], GrubStationManagerSwitch)


async def test_async_setup_entry_global(hass: HomeAssistant):
    """Test setup entry for global entry."""
    mock_entry = MagicMock()
    mock_entry.data = {}
    async_add_entities = MagicMock()

    await async_setup_entry(hass, mock_entry, async_add_entities)
    async_add_entities.assert_not_called()

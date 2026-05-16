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


async def test_async_turn_on_with_broadcast(hass, mock_coordinator):
    """Test turning the switch on with broadcast settings."""
    mock_coordinator.host.broadcast_address = "192.168.1.255"
    mock_coordinator.host.broadcast_port = 9
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock) as mock_job,
        patch("wakeonlan.send_magic_packet"),
    ):
        await switch.async_turn_on()
        mock_job.assert_called_once()
        # Verify kwargs passed to send_magic_packet
        args = mock_job.call_args[0][0].keywords
        assert args["ip_address"] == "192.168.1.255"
        assert args["port"] == 9


async def test_async_turn_off_no_action_no_agent(hass, mock_coordinator):
    """Test turning the switch off with no action or agent config."""
    mock_coordinator.host.address = None  # Make agent_is_configured false
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    await switch.async_turn_off()
    mock_coordinator.async_log_activity.assert_called_with("Shutdown requested (no action configured)")


async def test_async_turn_off_with_script(hass, mock_coordinator):
    """Test turning the switch off using a script."""
    mock_script = MagicMock()
    mock_script.async_run = AsyncMock()
    with patch("custom_components.grubstation.switch.Script", return_value=mock_script):
        switch = GrubStationManagerSwitch(hass, mock_coordinator)
        switch._turn_off_action = mock_script

        await switch.async_turn_off()
        mock_script.async_run.assert_awaited_once()


async def test_async_will_remove_from_hass(hass, mock_coordinator):
    """Test cleanup of background tasks."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)
    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    await switch.async_will_remove_from_hass()
    mock_task.cancel.assert_called_once()


async def test_async_verify_state(hass, mock_coordinator):
    """Test state verification logic."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch("custom_components.grubstation.switch.async_check_tcp_reachability", return_value=True),
        patch("asyncio.sleep"),
    ):
        await switch._async_verify_state(target_state=True)
        mock_coordinator.async_request_refresh.assert_awaited_once()


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


async def test_async_turn_off_agent_failure(hass, mock_coordinator):
    """Test shutdown command agent interaction failure."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch("custom_components.grubstation.switch.async_send_turn_off_command", side_effect=Exception("Failed")),
        pytest.raises(Exception, match="Failed"),
    ):
        await switch.async_turn_off()


async def test_async_verify_state_failure(hass, mock_coordinator):
    """Test state verification failure (timeout/no response)."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with (
        patch("custom_components.grubstation.switch.async_check_tcp_reachability", return_value=False),
        patch("asyncio.sleep"),
    ):
        # Run verify state, it should complete without refreshing
        await switch._async_verify_state(target_state=True)
        mock_coordinator.async_request_refresh.assert_not_awaited()


async def test_async_turn_on_verify_task_cancel(hass, mock_coordinator):
    """Test that existing ping task is cancelled on new turn_on."""
    switch = GrubStationManagerSwitch(hass, mock_coordinator)
    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    with patch("wakeonlan.send_magic_packet"):
        await switch.async_turn_on()
        mock_task.cancel.assert_called_once()


async def test_async_turn_off_no_address_no_ping(hass):
    """Test shutdown command with no address (coverage for switch.py:116)."""
    mock_host = RemoteHost(
        mac="00:11:22:33:44:55",
        address=None,
        agent_port=None,
        agent_token="test-token",
    )
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host
    mock_coordinator.async_log_activity = MagicMock()
    switch = GrubStationManagerSwitch(hass, mock_coordinator)

    with patch("custom_components.grubstation.switch.async_send_turn_off_command", new_callable=AsyncMock):
        await switch.async_turn_off()
        # Verify ping task is not created because no address
        assert switch._ping_task is None

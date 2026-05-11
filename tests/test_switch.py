"""Tests for GrubStation switch."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.switch import (
    GrubStationManagerSwitch,
    _async_ping_host,
    async_setup_entry,
)


async def test_async_ping_host_alive():
    """Test the async ping command when host is alive."""
    mock_result = MagicMock()
    mock_result.is_alive = True
    with patch(
        "custom_components.grubstation.switch.async_ping",
        return_value=mock_result,
    ):
        assert await _async_ping_host("192.168.1.10") is True


async def test_async_ping_host_dead():
    """Test the async ping command when host is dead or throws an error."""
    with patch(
        "custom_components.grubstation.switch.async_ping",
        side_effect=Exception("Boom"),
    ):
        assert await _async_ping_host("192.168.1.10") is False


async def test_switch_device_info(hass: HomeAssistant):
    """Test the device info for the switch."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    switch = GrubStationManagerSwitch(hass, host)
    assert switch.device_info is not None
    assert switch.device_info.get("name") == "00:11:22:33:44:55"
    assert switch.device_info.get("manufacturer") == "GrubStation"


async def test_switch_async_turn_on_starts_task(hass):
    """Test switch async_turn_on sends packet and starts the background ping loop."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    with (
        patch(
            "custom_components.grubstation.switch.wakeonlan.send_magic_packet"
        ) as mock_send,
        patch.object(hass, "async_create_background_task") as mock_task,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        await switch.async_turn_on()
        await hass.async_block_till_done()

        mock_send.assert_called_once_with("00:11:22:33:44:55")
        mock_task.assert_called_once()
        assert switch.is_on is True
        mock_write.assert_called_once()

        # Close the coroutine that was passed into the mock to prevent RuntimeWarnings
        mock_task.call_args[0][0].close()


async def test_switch_no_address_no_poll(hass):
    """Test that a host without a ping target doesn't poll or update state via ping."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    assert switch.should_poll is False

    with patch("custom_components.grubstation.switch._async_ping_host") as mock_ping:
        await switch.async_update()
        mock_ping.assert_not_called()


async def test_switch_async_turn_on_with_broadcast_and_cancels_task(hass):
    """Test sending a magic packet with custom broadcast data, cancelling old tasks."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
            broadcast_address="192.168.1.255",
            broadcast_port=9,
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    # Mock an existing active ping task
    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    with (
        patch(
            "custom_components.grubstation.switch.wakeonlan.send_magic_packet"
        ) as mock_send,
        patch.object(hass, "async_create_background_task") as mock_create_task,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        await switch.async_turn_on()
        await hass.async_block_till_done()

        mock_send.assert_called_once_with(
            "00:11:22:33:44:55", ip_address="192.168.1.255", port=9
        )
        mock_task.cancel.assert_called_once()
        mock_create_task.assert_called_once()
        assert switch.is_on is True
        mock_write.assert_called_once()

        # Close the coroutine that was passed into the mock to prevent RuntimeWarnings
        mock_create_task.call_args[0][0].close()


async def test_switch_async_turn_off(hass):
    """Test the turn off action."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass
    switch._attr_is_on = True

    mock_script = MagicMock()
    mock_script.async_run = AsyncMock()
    switch._turn_off_action = mock_script

    with (
        patch.object(hass, "async_create_background_task") as mock_task,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        await switch.async_turn_off()
        assert switch.is_on is False
        mock_write.assert_called_once()
        mock_script.async_run.assert_called_once()
        mock_task.assert_called_once()
        mock_task.call_args[0][0].close()


async def test_switch_async_turn_off_via_agent(hass: HomeAssistant) -> None:
    """Test the turn off action when it calls the remote agent directly."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="192.168.1.50",
        agent_port=8081,
        api_key="agent_secret",
        off_action=None,  # No script configured
    )
    switch = GrubStationManagerSwitch(hass, host)
    switch.hass = hass
    switch._attr_is_on = True

    with (
        patch(
            "custom_components.grubstation.switch.async_send_turn_off_command",
            new_callable=AsyncMock,
        ) as mock_agent_call,
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(hass, "async_create_background_task") as mock_task,
    ):
        await switch.async_turn_off()

        assert switch.is_on is False
        mock_agent_call.assert_called_once_with(
            hass, "192.168.1.50", 8081, "agent_secret"
        )
        mock_task.assert_called_once()
        mock_write.assert_called_once()
        mock_task.call_args[0][0].close()


async def test_switch_async_turn_off_cancels_task(hass):
    """Test that turn off cancels an existing ping task."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    with (
        patch.object(hass, "async_create_background_task") as mock_task_create,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        await switch.async_turn_off()
        mock_task.cancel.assert_called_once()
        mock_task_create.assert_called_once()
        mock_write.assert_called_once()
        mock_task_create.call_args[0][0].close()


async def test_switch_async_ping_loop_success(hass):
    """Test the background ping loop resolving successfully."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass
    switch._attr_is_on = True

    with (
        patch("asyncio.sleep"),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch(
            "custom_components.grubstation.switch._async_ping_host",
            side_effect=[False, True],
        ) as mock_ping,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=True)
        assert mock_ping.call_count == 2
        assert switch._attr_is_on is True
        mock_write.assert_not_called()


async def test_switch_async_ping_loop_timeout(hass):
    """Test the background ping loop timing out after 3 minutes."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass
    switch._attr_is_on = True

    with (
        patch("asyncio.sleep"),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch(
            "custom_components.grubstation.switch._async_ping_host",
            return_value=False,
        ) as mock_ping,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=True)
        assert mock_ping.call_count == 36
        assert switch._attr_is_on is False
        mock_write.assert_called_once()


async def test_switch_async_ping_loop_off_success(hass):
    """Test the background ping off loop resolving successfully."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass
    switch._attr_is_on = False

    with (
        patch("asyncio.sleep"),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch(
            "custom_components.grubstation.switch._async_ping_host",
            side_effect=[True, False],
        ) as mock_ping,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=False)
        assert mock_ping.call_count == 2
        assert switch._attr_is_on is False
        mock_write.assert_not_called()


async def test_switch_async_ping_loop_off_timeout(hass):
    """Test the background ping off loop timing out after 3 minutes."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass
    switch._attr_is_on = False

    with (
        patch("asyncio.sleep"),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch(
            "custom_components.grubstation.switch._async_ping_host",
            return_value=True,
        ) as mock_ping,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=False)
        assert mock_ping.call_count == 36
        assert switch._attr_is_on is True
        mock_write.assert_called_once()


async def test_async_setup_entry(hass):
    """Test the setup entry logic, including the dispatcher connection."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {
        "00:11:22:33:44:55": MagicMock(
            mac="00:11:22:33:44:55",
            address="test.local",
            off_action=None,
            broadcast_address=None,
            broadcast_port=None,
        ),
        "AA:BB:CC:DD:EE:FF": MagicMock(
            mac="AA:BB:CC:DD:EE:FF",
            address="test2.local",
            off_action=None,
            broadcast_address=None,
            broadcast_port=None,
        ),
    }
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch(
        "custom_components.grubstation.switch.async_dispatcher_connect"
    ) as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)

        # Both switch entities should be added
        assert async_add_entities.call_count == 2
        mock_connect.assert_called_once()
        mock_entry.async_on_unload.assert_called_once()

        # Verify the dispatcher callback adds the new entity
        callback = mock_connect.call_args[0][2]
        mock_manager.hosts["11:22:33:44:55:66"] = MagicMock(
            mac="11:22:33:44:55:66",
            address="new.local",
            off_action=None,
            broadcast_address=None,
            broadcast_port=None,
        )
        callback("11:22:33:44:55:66")
        assert async_add_entities.call_count == 3


async def test_async_update_skips_when_ping_task_active(hass):
    """Test that async_update skips polling if there is an active ping task."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    switch = GrubStationManagerSwitch(hass, host)

    # Mock an active ping task
    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    with patch("custom_components.grubstation.switch._async_ping_host") as mock_ping:
        await switch.async_update()
        # Polling should be skipped
        mock_ping.assert_not_called()


async def test_async_update_polls_when_no_active_task(hass):
    """Test that async_update polls normally if the ping task is done or None."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    switch = GrubStationManagerSwitch(hass, host)

    with patch(
        "custom_components.grubstation.switch._async_ping_host",
        return_value=True,
    ) as mock_ping:
        # Test when _ping_task is None
        switch._ping_task = None
        await switch.async_update()
        mock_ping.assert_called_once_with("test.local")
        assert switch._attr_is_on is True

    with patch(
        "custom_components.grubstation.switch._async_ping_host",
        return_value=False,
    ) as mock_ping:
        # Test when _ping_task is done
        mock_task = MagicMock()
        mock_task.done.return_value = True
        switch._ping_task = mock_task

        await switch.async_update()
        mock_ping.assert_called_once_with("test.local")
        assert switch._attr_is_on is False


async def test_switch_will_remove_from_hass_cancels_task(hass):
    """Test that removing the entity cancels an active ping task."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    await switch.async_will_remove_from_hass()

    mock_task.cancel.assert_called_once()


async def test_switch_will_remove_from_hass_ignores_done_task(hass):
    """Test that removing the entity ignores an already done ping task."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = True
    switch._ping_task = mock_task

    await switch.async_will_remove_from_hass()

    mock_task.cancel.assert_not_called()


async def test_switch_async_ping_loop_cancelled_initial_sleep(hass):
    """Test the background ping loop handles cancellation correctly during initial sleep."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    with (
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=True)
        # Should exit cleanly without throwing an exception or writing state
        mock_write.assert_not_called()


async def test_switch_async_ping_loop_cancelled_inner_sleep(hass):
    """Test the background ping loop handles cancellation correctly during loop sleep."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            address="test.local",
        )
    }
    switch = GrubStationManagerSwitch(hass, manager.hosts["00:11:22:33:44:55"])
    switch.hass = hass

    with (
        patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch(
            "custom_components.grubstation.switch._async_ping_host",
            return_value=False,
        ) as mock_ping,
    ):
        await switch._async_ping_loop("192.168.1.100", target_state=True)
        # Ping should be called once, then CancelledError breaks the loop cleanly
        mock_ping.assert_called_once()
        mock_write.assert_not_called()

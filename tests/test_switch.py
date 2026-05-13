"""Tests for GrubStation switch."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.grubstation.const import SIGNAL_NEW_HOST
from custom_components.grubstation.coordinator import GrubStationCoordinator
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.switch import (
    GrubStationManagerSwitch,
    _async_ping_host,
    async_setup_entry,
)


def get_mock_coordinator(hass: HomeAssistant, host: RemoteHost) -> MagicMock:
    """Return a mock coordinator."""
    coordinator = MagicMock(spec=GrubStationCoordinator)
    coordinator.hass = hass
    coordinator.data = host
    coordinator.host = host
    coordinator.manager = MagicMock()
    coordinator.manager.async_log_activity = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_async_ping_host_alive():
    """Test the async ping command when host is alive."""
    mock_result = MagicMock()
    mock_result.is_alive = True
    with patch(
        "custom_components.grubstation.coordinator.async_ping",
        return_value=mock_result,
    ):
        assert await _async_ping_host("192.168.1.10") is True


async def test_async_ping_host_dead():
    """Test the async ping command when host is dead or throws an error."""
    with patch(
        "custom_components.grubstation.coordinator.async_ping",
        side_effect=Exception("Boom"),
    ):
        assert await _async_ping_host("192.168.1.10") is False


async def test_switch_device_info(hass: HomeAssistant):
    """Test the device info for the switch."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    assert switch.device_info is not None
    assert switch.device_info.get("name") == "00:11:22:33:44:55"
    assert switch.device_info.get("manufacturer") == "GrubStation"


async def test_switch_async_turn_on_starts_task(hass):
    """Test switch async_turn_on sends packet and starts the background ping loop."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass

    with (
        patch(
            "custom_components.grubstation.switch.wakeonlan.send_magic_packet"
        ) as mock_send,
        patch.object(hass, "async_create_background_task") as mock_task_creator,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task_creator.return_value = mock_task

        await switch.async_turn_on()
        await hass.async_block_till_done()

        mock_send.assert_called_once_with("00:11:22:33:44:55")
        mock_task_creator.assert_called_once()
        assert switch.is_on is True
        mock_write.assert_called_once()

        # Close the coroutine that was passed into the mock to prevent RuntimeWarnings
        mock_task_creator.call_args[0][0].close()


async def test_switch_no_address_no_poll(hass):
    """Test that a host without a ping target has assumed_state True."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass

    assert switch.should_poll is False
    assert switch.assumed_state is True


async def test_switch_async_turn_on_with_broadcast_and_cancels_task(hass):
    """Test sending a magic packet with custom broadcast data, cancelling old tasks."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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
        new_mock_task = MagicMock()
        new_mock_task.done.return_value = False
        mock_create_task.return_value = new_mock_task

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
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        off_action={"service": "test.service"},
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass
    switch._attr_is_on = True

    mock_script = MagicMock()
    mock_script.async_run = AsyncMock()
    switch._turn_off_action = mock_script

    with (
        patch.object(hass, "async_create_background_task") as mock_task_creator,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task_creator.return_value = mock_task

        await switch.async_turn_off()
        assert switch.is_on is False
        mock_write.assert_called_once()
        mock_script.async_run.assert_called_once()
        mock_task_creator.assert_called_once()
        mock_task_creator.call_args[0][0].close()


async def test_switch_async_turn_off_via_daemon(hass: HomeAssistant) -> None:
    """Test the turn off action when it calls the remote daemon directly."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="192.168.1.50",
        daemon_port=8081,
        daemon_token="daemon_secret",  # noqa: S106
        off_action=None,  # No script configured
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass
    switch._attr_is_on = True

    with (
        patch(
            "custom_components.grubstation.switch.async_send_turn_off_command",
            new_callable=AsyncMock,
        ) as mock_daemon_call,
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(hass, "async_create_background_task") as mock_task_creator,
    ):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task_creator.return_value = mock_task

        await switch.async_turn_off()

        assert switch.is_on is False
        mock_daemon_call.assert_called_once_with(
            hass, "192.168.1.50", 8081, "daemon_secret"
        )
        mock_task_creator.assert_called_once()
        mock_write.assert_called_once()
        mock_task_creator.call_args[0][0].close()


async def test_switch_async_turn_off_cancels_task(hass):
    """Test that turn off cancels an existing ping task."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    with patch("custom_components.grubstation.switch.Script") as mock_script_class:
        mock_script = mock_script_class.return_value
        mock_script.async_run = AsyncMock()
        switch = GrubStationManagerSwitch(hass, coordinator)
        switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    with (
        patch.object(hass, "async_create_background_task") as mock_task_creator,
        patch.object(switch, "async_write_ha_state") as mock_write,
    ):
        new_mock_task = MagicMock()
        new_mock_task.done.return_value = False
        mock_task_creator.return_value = new_mock_task

        await switch.async_turn_off()
        mock_task.cancel.assert_called_once()
        mock_task_creator.assert_called_once()
        mock_write.assert_called_once()
        mock_task_creator.call_args[0][0].close()


async def test_switch_async_ping_loop_success(hass):
    """Test the background ping loop resolving successfully."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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
        coordinator.async_request_refresh.assert_called_once()


async def test_switch_async_ping_loop_timeout(hass):
    """Test the background ping loop timing out after 3 minutes."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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
        coordinator.async_request_refresh.assert_called_once()


async def test_switch_async_ping_loop_off_timeout(hass):
    """Test the background ping off loop timing out after 3 minutes."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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

    host1 = RemoteHost(mac="00:11:22:33:44:55", address="test1.local")
    host2 = RemoteHost(mac="AA:BB:CC:DD:EE:FF", address="test2.local")

    mock_manager.hosts = {
        host1.mac: host1,
        host2.mac: host2,
    }
    mock_manager.coordinators = {
        host1.mac: get_mock_coordinator(hass, host1),
        host2.mac: get_mock_coordinator(hass, host2),
    }
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch(
        "custom_components.grubstation.switch.async_dispatcher_connect"
    ) as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)

        # Both switch entities should be added
        assert async_add_entities.call_count == 2
        assert mock_connect.call_count == 2
        assert mock_entry.async_on_unload.call_count == 2

        # Verify the dispatcher callback adds the new entity
        callback = next(
            call[0][2]
            for call in mock_connect.call_args_list
            if call[0][1] == SIGNAL_NEW_HOST
        )
        host3 = RemoteHost(mac="11:22:33:44:55:66", address="new.local")
        mock_manager.hosts[host3.mac] = host3
        mock_manager.coordinators[host3.mac] = get_mock_coordinator(hass, host3)

        callback(host3.mac)
        assert async_add_entities.call_count == 3


async def test_async_setup_entry_no_coordinator(hass):
    """Test signal callback does not add entity if coordinator is missing."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = []
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch(
        "custom_components.grubstation.switch.async_dispatcher_connect"
    ) as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)
        callback = next(
            call[0][2]
            for call in mock_connect.call_args_list
            if call[0][1] == SIGNAL_NEW_HOST
        )
        callback("00:AA:BB:CC:DD:EE")
        assert async_add_entities.call_count == 0


async def test_switch_will_remove_from_hass_cancels_task(hass):
    """Test that removing the entity cancels an active ping task."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = False
    switch._ping_task = mock_task

    await switch.async_will_remove_from_hass()

    mock_task.cancel.assert_called_once()


async def test_switch_will_remove_from_hass_ignores_done_task(hass):
    """Test that removing the entity ignores an already done ping task."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
    switch.hass = hass

    mock_task = MagicMock()
    mock_task.done.return_value = True
    switch._ping_task = mock_task

    await switch.async_will_remove_from_hass()

    mock_task.cancel.assert_not_called()


async def test_switch_async_ping_loop_cancelled_initial_sleep(hass):
    """Test the background ping loop handles cancellation correctly during initial sleep."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = get_mock_coordinator(hass, host)
    switch = GrubStationManagerSwitch(hass, coordinator)
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

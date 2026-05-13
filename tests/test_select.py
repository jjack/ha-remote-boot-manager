"""Tests for GrubStation select platform."""

from unittest.mock import MagicMock, patch

from custom_components.grubstation.const import DEFAULT_BOOT_OPTION_NONE, SIGNAL_NEW_HOST
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.select import GrubStationManagerSelect, async_setup_entry


async def test_async_setup_entry(hass):
    """Test the setup entry logic, including the dispatcher connection."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_host = MagicMock()
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_host
    mock_coordinator.host = mock_host
    mock_manager.hosts = {mac: mock_host}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch("custom_components.grubstation.select.async_dispatcher_connect") as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)

        assert async_add_entities.call_count == 1
        assert mock_connect.call_count == 2
        assert mock_entry.async_on_unload.call_count == 2

        # Verify the dispatcher callback adds the new entity
        callback = next(call[0][2] for call in mock_connect.call_args_list if call[0][1] == SIGNAL_NEW_HOST)
        new_mac = "AA:BB:CC:DD:EE:FF"
        new_host = MagicMock()
        new_coordinator = MagicMock()
        new_coordinator.data = new_host
        new_coordinator.host = new_host
        mock_manager.hosts[new_mac] = new_host
        mock_manager.coordinators[new_mac] = new_coordinator
        callback(new_mac)
        assert async_add_entities.call_count == 2


async def test_async_setup_entry_duplicate_host(hass):
    """Test signal callback does not add entity if host already added."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mac = "00:11:22:33:44:55"
    mock_host = RemoteHost(mac=mac, address="1.2.3.4")
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host
    mock_manager.hosts = {mac: mock_host}
    mock_manager.coordinators = {mac: mock_coordinator}
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch("custom_components.grubstation.select.async_dispatcher_connect") as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)

        # First call adds the entity (from the setup loop)
        assert async_add_entities.call_count == 1

        # Get the callback
        callback = next(call[0][2] for call in mock_connect.call_args_list if call[0][1] == SIGNAL_NEW_HOST)

        # Call again with same MAC
        callback(mac)

        # async_add_entities should still be 1
        assert async_add_entities.call_count == 1


async def test_async_setup_entry_no_coordinator(hass):
    """Test signal callback does not add entity if coordinator is missing."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = []
    mock_manager.coordinators = {}
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch("custom_components.grubstation.select.async_dispatcher_connect") as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)
        callback = next(call[0][2] for call in mock_connect.call_args_list if call[0][1] == SIGNAL_NEW_HOST)
        callback("00:AA:BB:CC:DD:EE")
        assert async_add_entities.call_count == 0


async def test_select_init_model_name(hass):
    """Test the select entity initialization and model name generation."""
    manager = MagicMock()

    # With broadcast info
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        os="linux",
        broadcast_address="192.168.1.255",
        broadcast_port=9,
    )
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host

    select = GrubStationManagerSelect(manager, coordinator)
    assert select.device_info is not None
    assert select.device_info.get("name") == "00:11:22:33:44:55"
    assert select.device_info.get("model") == "test.local (Broadcast: 192.168.1.255)"

    # Without broadcast info
    host2 = RemoteHost(
        mac="AA:BB:CC:DD:EE:FF",
        address="test2.local",
        os="windows",
    )
    coordinator2 = MagicMock()
    coordinator2.data = host2
    coordinator2.host = host2

    select2 = GrubStationManagerSelect(manager, coordinator2)
    assert select2.device_info is not None
    assert select2.device_info.get("model") == "test2.local"

    # Without address
    host = RemoteHost(
        mac="00:11:22:33:44:55",
    )
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host

    select = GrubStationManagerSelect(manager, coordinator)
    assert select.device_info is not None
    assert select.device_info.get("name") == "00:11:22:33:44:55"
    assert select.device_info.get("model") == "GrubStation Host"


async def test_select_properties(hass):
    """Test the options and current_option properties."""
    manager = MagicMock()
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        boot_options=["ubuntu", "windows"],
        next_boot_option="windows",
    )
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host

    select = GrubStationManagerSelect(manager, coordinator)

    assert select.options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]
    assert select.current_option == "windows"

    # Test fallback when host missing (empty boot_options)
    host_missing = RemoteHost(mac="missing", address="missing")
    coordinator_missing = MagicMock()
    coordinator_missing.data = host_missing
    coordinator_missing.host = host_missing
    select_missing = GrubStationManagerSelect(manager, coordinator_missing)
    assert select_missing.options == [DEFAULT_BOOT_OPTION_NONE]
    assert select_missing.current_option == DEFAULT_BOOT_OPTION_NONE


async def test_async_select_option(hass):
    """Test selecting an option."""
    manager = MagicMock()
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host

    select = GrubStationManagerSelect(manager, coordinator)

    await select.async_select_option("ubuntu")
    manager.async_set_next_boot_option.assert_called_once_with("00:11:22:33:44:55", "ubuntu")

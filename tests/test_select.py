"""Tests for Grub OS Selector select platform."""

from unittest.mock import MagicMock, patch

from custom_components.grub_os_selector.const import DEFAULT_BOOT_OPTION_NONE
from custom_components.grub_os_selector.data import RemoteHost
from custom_components.grub_os_selector.select import (
    GrubOSSelectManagerSelect,
    async_setup_entry,
)


async def test_async_setup_entry(hass):
    """Test the setup entry logic, including the dispatcher connection."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {"00:11:22:33:44:55": MagicMock()}
    mock_entry.runtime_data = mock_manager
    async_add_entities = MagicMock()

    with patch(
        "custom_components.grub_os_selector.select.async_dispatcher_connect"
    ) as mock_connect:
        await async_setup_entry(hass, mock_entry, async_add_entities)

        assert async_add_entities.call_count == 1
        mock_connect.assert_called_once()
        mock_entry.async_on_unload.assert_called_once()

        # Verify the dispatcher callback adds the new entity
        callback = mock_connect.call_args[0][2]
        mock_manager.hosts["AA:BB:CC:DD:EE:FF"] = MagicMock()
        callback("AA:BB:CC:DD:EE:FF")
        assert async_add_entities.call_count == 2


async def test_select_init_model_name(hass):
    """Test the select entity initialization and model name generation."""
    manager = MagicMock()

    # With broadcast info
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            name="Test Host",
            address="test.local",
            broadcast_address="192.168.1.255",
            broadcast_port=9,
        )
    }
    select = GrubOSSelectManagerSelect(manager, "00:11:22:33:44:55")
    assert select.device_info is not None
    assert (
        select.device_info.get("model")
        == "Wake-on-LAN (Broadcast: 192.168.1.255, Port: 9)"
    )

    # Without broadcast info
    manager.hosts = {
        "AA:BB:CC:DD:EE:FF": RemoteHost(
            mac="AA:BB:CC:DD:EE:FF",
            name="Test Host 2",
            address="test2.local",
        )
    }
    select2 = GrubOSSelectManagerSelect(manager, "AA:BB:CC:DD:EE:FF")
    assert select2.device_info is not None
    assert select2.device_info.get("model") == "Wake-on-LAN"


async def test_select_properties(hass):
    """Test the options and current_option properties."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            name="Test",
            address="test.local",
            boot_options=["ubuntu", "windows"],
            next_boot_option="windows",
        )
    }
    select = GrubOSSelectManagerSelect(manager, "00:11:22:33:44:55")

    assert select.options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]
    assert select.current_option == "windows"

    # Test fallback when host missing
    select_missing = GrubOSSelectManagerSelect(manager, "00:11:22:33:44:55")
    select_missing.mac_address = "missing"
    assert select_missing.options == [DEFAULT_BOOT_OPTION_NONE]
    assert select_missing.current_option == DEFAULT_BOOT_OPTION_NONE


async def test_async_select_option(hass):
    """Test selecting an option."""
    manager = MagicMock()
    manager.hosts = {
        "00:11:22:33:44:55": RemoteHost(
            mac="00:11:22:33:44:55",
            name="Test",
            address="test.local",
        )
    }
    select = GrubOSSelectManagerSelect(manager, "00:11:22:33:44:55")

    await select.async_select_option("ubuntu")
    manager.async_set_next_boot_option.assert_called_once_with(
        "00:11:22:33:44:55", "ubuntu"
    )

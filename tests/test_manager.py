"""Tests for the GrubStationManager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.grubstation.const import DEFAULT_BOOT_OPTION_NONE
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.manager import GrubStationManager


@pytest.fixture
def mock_store():
    """Mock the HA Store implementation."""
    with patch("custom_components.grubstation.manager.Store") as mock_store_class:
        mock_instance = MagicMock()
        mock_instance.async_load = AsyncMock(return_value={})
        mock_instance.async_remove = AsyncMock()
        mock_store_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_coordinator():
    """Mock the GrubStationCoordinator."""
    with patch("custom_components.grubstation.manager.GrubStationCoordinator") as mock_class:
        mock_instance = MagicMock()
        mock_instance.async_refresh = AsyncMock()
        mock_instance.async_set_updated_data = MagicMock()
        mock_instance.host = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def manager(hass, mock_store, mock_coordinator):
    """Fixture for providing a clean GrubStationManager."""
    manager = GrubStationManager(hass)
    yield manager
    manager.async_unload()


async def test_async_register_agent_token_new_host(manager, hass, mock_coordinator):
    """Test that a new host is registered correctly."""
    payload = {
        "action": "register_agent_token",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "agent_port": 8000,
        "agent_token": "secret",
    }

    with patch("custom_components.grubstation.manager.async_dispatcher_send") as mock_dispatch:
        manager.async_register_agent_token("00:11:22:33:44:55", payload)

        assert "00:11:22:33:44:55" in manager.hosts
        assert "00:11:22:33:44:55" in manager.coordinators
        host = manager.hosts["00:11:22:33:44:55"]
        assert isinstance(host, RemoteHost)
        assert host.address == "test.local"
        assert host.agent_token == "secret"
        assert host.agent_port == 8000

        mock_dispatch.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once_with(host)


async def test_async_update_boot_options_new_host(manager, hass, mock_coordinator):
    """Test that receiving boot options for a new host creates it."""
    payload = {
        "action": "update_boot_options",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "boot_options": ["ubuntu", "windows"],
    }

    with patch("custom_components.grubstation.manager.async_dispatcher_send") as mock_dispatch:
        manager.async_update_boot_options("00:11:22:33:44:55", payload)

        assert "00:11:22:33:44:55" in manager.hosts
        host = manager.hosts["00:11:22:33:44:55"]
        assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]
        assert mock_dispatch.call_count == 2
        mock_coordinator.async_set_updated_data.assert_called()


async def test_async_update_boot_options_none_option_already_present(manager, hass, mock_coordinator):
    """Test that the default none boot option is not duplicated if already present."""
    # Setup host first via registration
    reg_payload = {
        "action": "register_agent_token",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "agent_token": "secret",
        "agent_port": 8000,
    }
    manager.async_register_agent_token("00:11:22:33:44:55", reg_payload)

    push_payload = {
        "action": "update_boot_options",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "boot_options": [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"],
    }

    manager.async_update_boot_options("00:11:22:33:44:55", push_payload)

    host = manager.hosts["00:11:22:33:44:55"]
    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]
    # Once for registration, once for push
    assert mock_coordinator.async_set_updated_data.call_count == 2


async def test_async_update_boot_options_empty_boot_options(manager, hass, mock_coordinator):
    """Test that DEFAULT_BOOT_OPTION_NONE is added when boot_options is empty."""
    # Setup host
    reg_payload = {
        "action": "register_agent_token",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "agent_token": "secret",
        "agent_port": 8000,
    }
    manager.async_register_agent_token("00:11:22:33:44:55", reg_payload)

    push_payload = {
        "action": "update_boot_options",
        "mac": "00:11:22:33:44:55",
        "address": "test.local",
        "boot_options": [],
    }

    manager.async_update_boot_options("00:11:22:33:44:55", push_payload)

    host = manager.hosts["00:11:22:33:44:55"]
    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE]


async def test_async_update_boot_options_update_existing_host(manager, hass, mock_coordinator):
    """Test that an existing host is updated correctly."""
    # Setup existing host
    mac = "00:11:22:33:44:55"
    host = RemoteHost(
        mac=mac,
        address="old-hostname.local",
        os="linux",
        boot_options=["ubuntu"],
    )
    manager.hosts[mac] = host
    manager.coordinators[mac] = mock_coordinator

    payload = {
        "action": "update_boot_options",
        "mac": mac,
        "address": "new-hostname.local",
        "boot_options": ["ubuntu", "arch"],
    }

    manager.async_update_boot_options(mac, payload)

    assert host.address == "new-hostname.local"
    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "arch"]
    mock_coordinator.async_set_updated_data.assert_called_once_with(host)


async def test_async_set_and_consume_next_boot_option(manager, hass, mock_coordinator):
    """Test setting and safely consuming the next boot option."""
    mac = "00:11:22:33:44:55"
    host = RemoteHost(
        mac=mac,
        address="test.local",
        boot_options=[DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"],
    )
    manager.hosts[mac] = host
    manager.coordinators[mac] = mock_coordinator

    # Set the option
    manager.async_set_next_boot_option(mac, "windows")
    assert host.next_boot_option == "windows"
    mock_coordinator.async_set_updated_data.assert_called_with(host)

    # Consume the option (should return it, and reset state)
    consumed = manager.async_consume_next_boot_option(mac)
    assert consumed == "windows"
    assert host.next_boot_option == DEFAULT_BOOT_OPTION_NONE
    mock_coordinator.async_set_updated_data.assert_called_with(host)


async def test_async_remove_host_invalid_mac(manager, hass):
    """Test removing a non-existent host does nothing."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    with patch.object(manager, "save") as mock_save:
        manager.async_remove_host("FF:FF:FF:FF:FF:FF")
        assert "00:11:22:33:44:55" in manager.hosts
        mock_save.assert_not_called()


async def test_async_load_no_data(manager, mock_store):
    """Test loading from an empty or non-existent store."""
    mock_store.async_load.return_value = None
    await manager.async_load()
    assert manager.hosts == {}

    mock_store.async_load.return_value = {"other_key": "other_value"}
    await manager.async_load()
    assert manager.hosts == {}


async def test_async_load_valid_data(manager, mock_store, mock_coordinator):
    """Test loading valid host data from storage."""
    mock_store.async_load.return_value = {
        "hosts": {
            "00:11:22:33:44:55": {
                "mac": "00:11:22:33:44:55",
                "address": "stored.local",
                "name": "Stored Host",
            }
        }
    }
    await manager.async_load()

    assert "00:11:22:33:44:55" in manager.hosts
    assert "00:11:22:33:44:55" in manager.coordinators
    host = manager.hosts["00:11:22:33:44:55"]
    assert host.address == "stored.local"
    mock_coordinator.async_refresh.assert_awaited_once()


async def test_async_load_invalid_data_format(manager, mock_store):
    """Test loading invalid host data format logs a warning and skips it."""
    mock_store.async_load.return_value = {"hosts": {"00:11:22:33:44:55": ["list", "instead", "of", "dict"]}}

    with patch("custom_components.grubstation.manager.LOGGER.warning") as mock_warn:
        await manager.async_load()

    assert "00:11:22:33:44:55" not in manager.hosts
    mock_warn.assert_called_once()
    assert "Discarding invalid host data" in mock_warn.call_args[0][0]


async def test_async_load_filters_extra_keys(manager, mock_store, mock_coordinator):
    """Test loading data with unknown keys correctly filters them out."""
    mock_store.async_load.return_value = {
        "hosts": {
            "00:11:22:33:44:55": {
                "mac": "00:11:22:33:44:55",
                "address": "filtered.local",
                "name": "Filtered Host",
                "unknown_future_key": "some_value",
            }
        }
    }

    await manager.async_load()

    assert "00:11:22:33:44:55" in manager.hosts
    host = manager.hosts["00:11:22:33:44:55"]
    assert not hasattr(host, "unknown_future_key")


async def test_async_purge_data(manager, mock_store):
    """Test that purging data clears hosts and removes the store file."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(mac="00:11:22:33:44:55", address="test.local")
    await manager.async_purge_data()
    assert not manager.hosts
    assert not manager.coordinators
    mock_store.async_remove.assert_awaited_once()


async def test_async_update_boot_options_resets_invalid_next_boot(manager, hass, mock_coordinator):
    """Test that next_boot_option is reset if it becomes invalid after an update."""
    mac = "00:11:22:33:44:55"
    host = RemoteHost(
        mac=mac,
        address="test.local",
        os="linux",
        boot_options=["ubuntu", "windows"],
        next_boot_option="windows",  # This will become invalid
    )
    manager.hosts[mac] = host
    manager.coordinators[mac] = mock_coordinator
    payload = {
        "action": "update_boot_options",
        "mac": mac,
        "address": "test.local",
        "boot_options": ["ubuntu", "fedora"],
    }

    manager.async_update_boot_options(mac, payload)

    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "fedora"]
    assert host.next_boot_option == DEFAULT_BOOT_OPTION_NONE
    mock_coordinator.async_set_updated_data.assert_called_once_with(host)


async def test_async_set_next_boot_option_invalid_mac(manager, hass):
    """Test setting a boot option for a non-existent MAC does nothing."""
    with patch("custom_components.grubstation.manager.async_dispatcher_send") as mock_dispatch:
        manager.async_set_next_boot_option("FF:FF:FF:FF:FF:FF", "windows")
        assert "FF:FF:FF:FF:FF:FF" not in manager.hosts
        mock_dispatch.assert_not_called()


async def test_async_consume_next_boot_option_invalid_mac(manager, hass):
    """Test consuming a boot option for a non-existent MAC returns default."""
    consumed = manager.async_consume_next_boot_option("FF:FF:FF:FF:FF:FF")
    assert consumed == DEFAULT_BOOT_OPTION_NONE


async def test_async_remove_host(manager, hass, mock_coordinator):
    """Test removing a host from the manager."""
    mac = "00:11:22:33:44:55"
    manager.hosts[mac] = RemoteHost(
        mac=mac,
        address="test.local",
    )
    manager.coordinators[mac] = mock_coordinator

    manager.async_remove_host(mac)
    assert mac not in manager.hosts
    assert mac not in manager.coordinators


async def test_save(manager, mock_store):
    """Test the save method calls delay save with correct data."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    manager.save()
    mock_store.async_delay_save.assert_called_once()
    # Verify the callback returns expected data
    save_callback = mock_store.async_delay_save.call_args[0][0]
    data = save_callback()
    assert "00:11:22:33:44:55" in data["hosts"]

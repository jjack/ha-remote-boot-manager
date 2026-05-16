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
        mock_instance.async_update_host_data = AsyncMock()
        mock_instance.host = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def manager(hass, mock_store, mock_coordinator):
    """Fixture for providing a clean GrubStationManager."""
    manager = GrubStationManager(hass)
    yield manager
    manager.async_unload()


async def test_async_process_payload_existing_host(manager, hass, mock_coordinator):
    """Test that an existing host is updated via process_payload."""
    mac = "00:11:22:33:44:55"
    manager.hosts[mac] = RemoteHost(mac=mac)
    manager.coordinators[mac] = mock_coordinator

    payload = {
        "action": "update_boot_options",
        "mac": mac,
        "address": "new.local",
    }

    await manager.async_process_payload(mac, payload)

    mock_coordinator.async_update_host_data.assert_called_once_with(payload)


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


async def test_async_purge_data(manager, mock_store):
    """Test that purging data clears hosts and removes the store file."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(mac="00:11:22:33:44:55", address="test.local")
    await manager.async_purge_data()
    assert not manager.hosts
    assert not manager.coordinators
    mock_store.async_remove.assert_awaited_once()


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

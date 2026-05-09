"""Tests for the GrubStationManager."""

from datetime import UTC, datetime
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
def manager(hass, mock_store):
    """Fixture for providing a clean GrubStationManager."""
    manager = GrubStationManager(hass)
    yield manager
    manager.async_unload()


async def test_async_process_webhook_payload_new_host(manager, hass):
    """Test that a new host is added correctly from a payload."""
    payload = {
        "address": "test.local",
        "name": "test-host",
        "boot_options": ["ubuntu", "windows"],
        "broadcast_address": "192.168.1.255",
        "broadcast_port": 9,
    }

    with patch(
        "custom_components.grubstation.manager.async_dispatcher_send"
    ) as mock_dispatch:
        manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

        assert "00:11:22:33:44:55" in manager.hosts
        host = manager.hosts["00:11:22:33:44:55"]
        assert isinstance(host, RemoteHost)
        assert host.name == "test-host"
        assert host.address == "test.local"
        # make sure that (none) is prepended
        assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]
        assert host.broadcast_address == "192.168.1.255"
        assert host.broadcast_port == 9

        mock_dispatch.assert_called_once()


async def test_async_process_webhook_payload_none_option_already_present(manager, hass):
    """Test that the default none boot option is not duplicated if already present."""
    payload = {
        "address": "test.local",
        "name": "test-host",
        "boot_options": [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"],
    }

    manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

    host = manager.hosts["00:11:22:33:44:55"]
    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"]


async def test_async_process_webhook_payload_update_existing_host(manager, hass):
    """Test that an existing host is updated correctly, including device registry rename."""
    # Setup existing host
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="old-hostname.local",
        name="old-hostname",
        boot_options=["ubuntu"],
    )

    payload = {
        "address": "new-hostname.local",
        "name": "new-hostname",
        "boot_options": ["ubuntu", "arch"],
        "broadcast_address": "10.0.0.255",
        "broadcast_port": 7,
    }

    with patch("custom_components.grubstation.manager.dr.async_get") as mock_dr:
        mock_registry = MagicMock()
        mock_dr.return_value = mock_registry
        mock_device = MagicMock()
        mock_device.id = "device_123"
        mock_registry.async_get_device.return_value = mock_device

        manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

        host = manager.hosts["00:11:22:33:44:55"]
        assert host.name == "new-hostname"
        assert host.address == "new-hostname.local"
        assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "arch"]
        assert host.broadcast_address == "10.0.0.255"
        assert host.broadcast_port == 7

        # Verify device registry was updated with the new hostname
        mock_registry.async_update_device.assert_called_once_with(
            "device_123", name="new-hostname"
        )


async def test_async_set_and_consume_next_boot_option(manager, hass):
    """Test setting and safely consuming the next boot option."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
        boot_options=[DEFAULT_BOOT_OPTION_NONE, "ubuntu", "windows"],
    )

    # Set the option
    manager.async_set_next_boot_option("00:11:22:33:44:55", "windows")
    assert manager.hosts["00:11:22:33:44:55"].next_boot_option == "windows"

    # Consume the option (should return it, and reset state)
    consumed = manager.async_consume_next_boot_option("00:11:22:33:44:55")
    assert consumed == "windows"
    assert (
        manager.hosts["00:11:22:33:44:55"].next_boot_option == DEFAULT_BOOT_OPTION_NONE
    )


async def test_async_remove_host_invalid_mac(manager, hass):
    """Test removing a non-existent host does nothing."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
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


async def test_async_load_valid_data(manager, mock_store):
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
    host = manager.hosts["00:11:22:33:44:55"]
    assert host.address == "stored.local"
    assert host.name == "Stored Host"


async def test_async_load_invalid_data_format(manager, mock_store):
    """Test loading invalid host data format logs a warning and skips it."""
    mock_store.async_load.return_value = {
        "hosts": {"00:11:22:33:44:55": ["list", "instead", "of", "dict"]}
    }

    with patch("custom_components.grubstation.manager.LOGGER.warning") as mock_warn:
        await manager.async_load()

    assert "00:11:22:33:44:55" not in manager.hosts
    mock_warn.assert_called_once()
    assert "Discarding invalid host data" in mock_warn.call_args[0][0]


async def test_async_load_filters_extra_keys(manager, mock_store):
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
    assert host.name == "Filtered Host"
    assert not hasattr(host, "unknown_future_key")


async def test_async_purge_data(manager, mock_store):
    """Test that purging data clears hosts and removes the store file."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55", name="test", address="test.local"
    )
    await manager.async_purge_data()
    assert not manager.hosts
    mock_store.async_remove.assert_awaited_once()


async def test_async_process_webhook_payload_update_no_rename(manager, hass):
    """Test that an existing host is updated without renaming the device."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="same-hostname.local",
        name="same-hostname",
        boot_options=["ubuntu"],
    )

    payload = {
        "address": "same-hostname.local",
        "name": "same-hostname",  # name is the same
        "boot_options": ["ubuntu", "arch"],
    }

    with patch("custom_components.grubstation.manager.dr.async_get") as mock_dr:
        mock_registry = MagicMock()
        mock_dr.return_value = mock_registry

        manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

        host = manager.hosts["00:11:22:33:44:55"]
        assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "arch"]

        # Verify device registry was NOT updated
        mock_registry.async_update_device.assert_not_called()


async def test_async_process_webhook_payload_update_device_not_found(manager, hass):
    """Test that an update with a rename does not fail if the device is not found."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="old-hostname.local",
        name="old-hostname",
    )
    payload = {"address": "old-hostname.local", "name": "new-hostname"}

    with patch("custom_components.grubstation.manager.dr.async_get") as mock_dr:
        mock_registry = MagicMock()
        mock_dr.return_value = mock_registry
        mock_registry.async_get_device.return_value = None  # Device not found

        manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

        host = manager.hosts["00:11:22:33:44:55"]
        assert host.name == "new-hostname"
        mock_registry.async_update_device.assert_not_called()


async def test_async_process_webhook_payload_resets_invalid_next_boot(manager, hass):
    """Test that next_boot_option is reset if it becomes invalid after an update."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
        boot_options=["ubuntu", "windows"],
        next_boot_option="windows",  # This will become invalid
    )
    payload = {
        "address": "test.local",
        "name": "test-host",
        "boot_options": ["ubuntu", "fedora"],
    }

    manager.async_process_webhook_payload("00:11:22:33:44:55", payload)

    host = manager.hosts["00:11:22:33:44:55"]
    assert host.boot_options == [DEFAULT_BOOT_OPTION_NONE, "ubuntu", "fedora"]
    assert host.next_boot_option == DEFAULT_BOOT_OPTION_NONE


async def test_async_set_next_boot_option_invalid_mac(manager, hass):
    """Test setting a boot option for a non-existent MAC does nothing."""
    with patch(
        "custom_components.grubstation.manager.async_dispatcher_send"
    ) as mock_dispatch:
        manager.async_set_next_boot_option("FF:FF:FF:FF:FF:FF", "windows")
        assert "FF:FF:FF:FF:FF:FF" not in manager.hosts
        mock_dispatch.assert_not_called()


async def test_async_consume_next_boot_option_invalid_mac(manager, hass):
    """Test consuming a boot option for a non-existent MAC returns default."""
    consumed = manager.async_consume_next_boot_option("FF:FF:FF:FF:FF:FF")
    assert consumed == DEFAULT_BOOT_OPTION_NONE


async def test_async_remove_host(manager, hass):
    """Test removing a host from the manager."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
    )

    manager.async_remove_host("00:11:22:33:44:55")
    assert "00:11:22:33:44:55" not in manager.hosts


async def test_save(manager, mock_store):
    """Test the save method calls delay save with correct data."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
    )
    manager.save()
    mock_store.async_delay_save.assert_called_once()
    # Verify the callback returns expected data
    save_callback = mock_store.async_delay_save.call_args[0][0]
    data = save_callback()
    assert "00:11:22:33:44:55" in data["hosts"]
    assert data["hosts"]["00:11:22:33:44:55"]["name"] == "test-host"


async def test_async_poll_agent_status_success(manager, hass):
    """Test polling agent status sets is_agent_accessible and last_agent_accessible correctly."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
        agent_port=8081,
        api_key="secret",
        is_agent_accessible=False,
    )
    now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch(
            "custom_components.grubstation.manager.async_check_agent_status",
            return_value=True,
        ) as mock_check,
        patch(
            "custom_components.grubstation.manager.async_dispatcher_send"
        ) as mock_dispatch,
        patch.object(manager, "save") as mock_save,
    ):
        await manager.async_poll_agent_status(now)

        mock_check.assert_called_once_with(hass, "test.local", 8081, "secret")

        host = manager.hosts["00:11:22:33:44:55"]
        assert host.is_agent_accessible is True
        assert host.last_agent_accessible == now.isoformat()

        mock_save.assert_called_once()
        mock_dispatch.assert_called_once_with(
            hass, "grubstation_update_00:11:22:33:44:55"
        )


async def test_async_poll_agent_status_failure(manager, hass):
    """Test polling agent status handles failure and updates state."""
    manager.hosts["00:11:22:33:44:55"] = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        name="test-host",
        agent_port=8081,
        api_key="secret",
        is_agent_accessible=True,
        last_agent_accessible="2023-01-01T12:00:00+00:00",
    )
    now = datetime(2023, 1, 1, 12, 1, 0, tzinfo=UTC)

    with (
        patch(
            "custom_components.grubstation.manager.async_check_agent_status",
            return_value=False,
        ) as mock_check,
        patch(
            "custom_components.grubstation.manager.async_dispatcher_send"
        ) as mock_dispatch,
        patch.object(manager, "save") as mock_save,
    ):
        await manager.async_poll_agent_status(now)

        mock_check.assert_called_once_with(hass, "test.local", 8081, "secret")

        host = manager.hosts["00:11:22:33:44:55"]
        assert host.is_agent_accessible is False
        assert (
            host.last_agent_accessible == "2023-01-01T12:00:00+00:00"
        )  # should remain unchanged

        mock_save.assert_called_once()
        mock_dispatch.assert_called_once_with(
            hass, "grubstation_update_00:11:22:33:44:55"
        )

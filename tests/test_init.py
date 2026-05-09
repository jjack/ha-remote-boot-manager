"""Tests for grubstation __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_ADDRESS, CONF_API_KEY, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation import (
    async_reload_entry,
    async_remove_config_entry_device,
    async_remove_entry,
    async_setup,
    async_setup_entry,
)
from custom_components.grubstation.const import DOMAIN


async def test_async_remove_entry_with_runtime_data(hass):
    """Test async_remove_entry when the integration is loaded."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.async_purge_data = AsyncMock()
    mock_entry.runtime_data = mock_manager

    await async_remove_entry(hass, mock_entry)

    mock_manager.async_purge_data.assert_awaited_once()


async def test_async_remove_entry_without_runtime_data(hass):
    """Test async_remove_entry when the integration is unloaded."""
    mock_entry = MagicMock()
    del mock_entry.runtime_data  # Ensure hasattr returns False

    with patch("custom_components.grubstation.Store") as mock_store_class:
        mock_store_instance = AsyncMock()
        mock_store_class.return_value = mock_store_instance

        await async_remove_entry(hass, mock_entry)

        mock_store_class.assert_called_once_with(hass, 1, f"{DOMAIN}.hosts")
        mock_store_instance.async_remove.assert_awaited_once()


async def test_async_reload_entry(hass):
    """Test that async_reload_entry calls the underlying reload function."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"

    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        await async_reload_entry(hass, mock_entry)
        mock_reload.assert_awaited_once_with("test_entry_id")


async def test_async_remove_config_entry_device(hass):
    """Test that removing a device also removes the host from the manager."""
    mock_manager = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.runtime_data = mock_manager

    mock_device_entry = MagicMock()
    mock_device_entry.identifiers = {(DOMAIN, "00:11:22:33:44:55")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, mock_device_entry
    )

    assert result is True
    mock_manager.async_remove_host.assert_called_once_with("00:11:22:33:44:55")


async def test_async_remove_config_entry_device_no_match(hass):
    """Test that removing a device with no matching identifier does nothing."""
    mock_manager = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.runtime_data = mock_manager

    mock_device_entry = MagicMock()
    mock_device_entry.identifiers = {("other_domain", "some_id")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, mock_device_entry
    )

    assert result is True
    mock_manager.async_remove_host.assert_not_called()


async def test_async_setup_entry(hass):
    """Test that setup adds an update listener and registers a webhook."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    with (
        patch("custom_components.grubstation.manager.GrubStationManager.async_load"),
        patch("homeassistant.components.webhook.async_register") as mock_register,
        patch.object(hass.config_entries, "async_forward_entry_setups"),
        patch.object(entry, "add_update_listener") as mock_add_listener,
        patch.object(entry, "async_on_unload") as mock_on_unload,
    ):
        assert await async_setup_entry(hass, entry) is True
        mock_register.assert_called_once()
        mock_add_listener.assert_called_once_with(async_reload_entry)
        mock_on_unload.assert_called()


async def test_async_setup_registers_send_turn_off_service(hass):
    """Test that async_setup registers the send_turn_off_command service."""
    hass.http = MagicMock()

    with (
        patch.object(hass.http, "register_view") as mock_register_view,
        patch(
            "custom_components.grubstation.async_send_turn_off_command",
            new_callable=AsyncMock,
        ) as mock_send_off,
    ):
        assert await async_setup(hass, {}) is True

        mock_register_view.assert_called_once()

        await hass.services.async_call(
            DOMAIN,
            "send_turn_off_command",
            {
                CONF_ADDRESS: "1.2.3.4",
                CONF_PORT: 1234,
                CONF_API_KEY: "secret_key",
            },
            blocking=True,
        )

        mock_send_off.assert_awaited_once_with(hass, "1.2.3.4", 1234, "secret_key")

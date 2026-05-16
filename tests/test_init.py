"""Tests for grubstation __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation import async_remove_config_entry, async_setup, async_setup_entry, async_unload_entry
from custom_components.grubstation.const import DOMAIN


async def test_async_setup_registers_send_turn_off_service(hass):
    """Test that async_setup registers the send_turn_off_command service."""
    # Mock http component to allow register_view to succeed
    hass.config.components.add("http")
    hass.http = MagicMock()

    with (
        patch.object(hass.http, "register_view") as mock_register_view,
        patch(
            "custom_components.grubstation.async_send_turn_off_command",
            new_callable=AsyncMock,
        ),
    ):
        assert await async_setup(hass, {}) is True

        mock_register_view.assert_called_once()
        assert hass.services.has_service(DOMAIN, "send_turn_off_command")


async def test_async_setup_entry_global(hass):
    """Test that setting up the global entry registers a webhook."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    with (
        patch("custom_components.grubstation.manager.GrubStationManager.async_load") as mock_load,
        patch("homeassistant.components.webhook.async_register") as mock_register,
    ):
        assert await async_setup_entry(hass, entry) is True
        mock_register.assert_called_once()
        mock_load.assert_called_once()
        assert isinstance(entry.runtime_data, MagicMock) is False  # It should be a real manager


async def test_async_unload_entry_global(hass):
    """Test async_unload_entry for the global entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.runtime_data = MagicMock()

    with (
        patch("homeassistant.components.webhook.async_unregister") as mock_unregister,
    ):
        result = await async_unload_entry(hass, entry)
        assert result is True
        mock_unregister.assert_called_once_with(hass, "test_id")
        entry.runtime_data.async_unload.assert_called_once()


async def test_async_remove_config_entry_global(hass):
    """Test async_remove_config_entry for global entry purges store."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})

    with patch("custom_components.grubstation.Store.async_remove") as mock_remove:
        await async_remove_config_entry(hass, entry)
        mock_remove.assert_called_once()

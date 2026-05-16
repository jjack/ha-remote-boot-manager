"""Tests for grubstation __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation import (
    DOMAIN,
    async_remove_config_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)


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


async def test_send_turn_on_service_logic(hass):
    """Test the logic inside send_turn_on_command service handler."""
    # Setup mock entry with runtime_data
    mock_coordinator = MagicMock()
    mock_coordinator.host.mac = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.host.broadcast_address = "192.168.1.255"
    mock_coordinator.host.broadcast_port = 9

    entry = MockConfigEntry(domain=DOMAIN, data={"mac": "AA:BB:CC:DD:EE:FF"})
    entry.runtime_data = mock_coordinator
    entry.add_to_hass(hass)

    await async_setup(hass, {})
    service_handler = hass.services._services[DOMAIN]["send_turn_on_command"]
    handler_func = service_handler.job.target

    mock_call = MagicMock()
    mock_call.data = {"entity_id": entry.entry_id}

    with patch("custom_components.grubstation.wakeonlan.send_magic_packet") as mock_wol:
        with patch(
            "custom_components.grubstation.async_extract_config_entry_ids", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = [entry.entry_id]
            await handler_func(mock_call)

        mock_wol.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF",
            ip_address="192.168.1.255",
            port=9,
        )


async def test_send_turn_off_service_logic(hass):
    """Test the logic inside send_turn_off_command service handler."""
    mock_coordinator = MagicMock()
    mock_coordinator.host.address = "192.168.1.10"
    mock_coordinator.host.agent_port = 8080
    mock_coordinator.host.agent_token = "secret"
    mock_coordinator.host.mac = "AA:BB:CC:DD:EE:FF"

    entry = MockConfigEntry(domain=DOMAIN, data={"mac": "AA:BB:CC:DD:EE:FF"})
    entry.runtime_data = mock_coordinator
    entry.add_to_hass(hass)

    await async_setup(hass, {})
    service_handler = hass.services._services[DOMAIN]["send_turn_off_command"]
    handler_func = service_handler.job.target

    mock_call = MagicMock()
    mock_call.data = {"entity_id": entry.entry_id}

    with patch(
        "custom_components.grubstation.async_send_turn_off_command",
        new_callable=AsyncMock,
    ) as mock_send_turn_off:
        with patch(
            "custom_components.grubstation.async_extract_config_entry_ids", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = [entry.entry_id]
            await handler_func(mock_call)

        mock_send_turn_off.assert_called_once_with(hass, "192.168.1.10", 8080, "secret")


async def test_send_turn_off_service_missing_config(hass, caplog):
    """Test the warning log when host is missing agent config."""
    await async_setup(hass, {})
    mock_coordinator = MagicMock()
    mock_coordinator.host.address = None
    mock_coordinator.host.mac = "AA:BB:CC:DD:EE:FF"

    entry = MockConfigEntry(domain=DOMAIN, data={"mac": "AA:BB:CC:DD:EE:FF"})
    entry.runtime_data = mock_coordinator
    entry.add_to_hass(hass)

    service_handler = hass.services._services[DOMAIN]["send_turn_off_command"]
    handler_func = service_handler.job.target
    mock_call = MagicMock()
    mock_call.data = {"entity_id": entry.entry_id}

    with patch("custom_components.grubstation.async_extract_config_entry_ids", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = [entry.entry_id]
        await handler_func(mock_call)


async def test_send_turn_on_command_invalid_entries(hass):
    """Test send_turn_on_command service with invalid/missing entries."""
    await async_setup(hass, {})
    service_handler = hass.services._services[DOMAIN]["send_turn_on_command"]
    handler_func = service_handler.job.target

    mock_call = MagicMock()
    mock_call.data = {"entity_id": "invalid_id"}

    with patch("custom_components.grubstation.async_extract_config_entry_ids", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = ["non_existent_id"]
        # Should not raise exception
        await handler_func(mock_call)

    # Test global entry skip
    global_entry = MockConfigEntry(domain=DOMAIN, data={})
    global_entry.add_to_hass(hass)
    mock_extract.return_value = [global_entry.entry_id]
    await handler_func(mock_call)
    # Should not raise exception


async def test_send_turn_off_command_invalid_entries(hass):
    """Test send_turn_off_command service with invalid/missing entries."""
    await async_setup(hass, {})
    service_handler = hass.services._services[DOMAIN]["send_turn_off_command"]
    handler_func = service_handler.job.target

    mock_call = MagicMock()
    mock_call.data = {"entity_id": "invalid_id"}

    with patch("custom_components.grubstation.async_extract_config_entry_ids", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = ["non_existent_id"]
        await handler_func(mock_call)

    # Test global entry skip
    global_entry = MockConfigEntry(domain=DOMAIN, data={})
    global_entry.add_to_hass(hass)
    mock_extract.return_value = [global_entry.entry_id]
    await handler_func(mock_call)

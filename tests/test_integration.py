"""Test integration for grubstation."""

from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation import async_reload_entry, async_remove_config_entry_device
from custom_components.grubstation.const import DEFAULT_BOOT_OPTION_NONE, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_dr
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.setup import async_setup_component


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="GrubStation",
        data={"webhook_id": "test_webhook_id"},
    )


@pytest.fixture
async def setup_integration(hass: HomeAssistant, hass_client, mock_config_entry):
    """Set up the integration and return the web client."""
    mock_config_entry.add_to_hass(hass)

    await async_setup_component(hass, "homeassistant", {})
    await async_setup_component(hass, "http", {})
    await async_setup_component(hass, "webhook", {})
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return await hass_client()


@pytest.fixture
async def discovered_client(hass: HomeAssistant, setup_integration):
    """Return a client after discovering a test host via boot options webhook."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "update_boot_options",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
        "boot_options": ["ubuntu", "windows"],
    }
    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK

    await hass.async_block_till_done()
    return client


async def test_webhook_discovery_boot_options(hass: HomeAssistant, setup_integration) -> None:
    """Test that posting boot options to the webhook creates the appropriate entities."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "update_boot_options",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
        "boot_options": ["ubuntu", "windows"],
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    entity_id_select = "select.aa_bb_cc_dd_ee_ff_next_boot_option"
    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.state == DEFAULT_BOOT_OPTION_NONE


async def test_webhook_discovery_daemon_token(hass: HomeAssistant, setup_integration) -> None:
    """Test that posting to the webhook creates the appropriate entities."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "register_daemon_token",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
        "daemon_port": 8000,
        "daemon_token": "secret",
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    # The entity ID is based on the MAC address since 'name' is removed from webhook
    entity_id_select = "select.aa_bb_cc_dd_ee_ff_next_boot_option"
    entity_id_switch = "switch.aa_bb_cc_dd_ee_ff_wake"

    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.state == DEFAULT_BOOT_OPTION_NONE

    state = hass.states.get(entity_id_switch)
    assert state is not None


async def test_minimal_webhook_discovery_and_switch(hass: HomeAssistant, setup_integration) -> None:
    """Test discovery and switch functionality with a minimal payload (mac)."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "register_daemon_token",
        "mac": "de:ad:be:ef:00:01",
        "address": "minimal.local",
        "daemon_port": 8000,
        "daemon_token": "secret",
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    # Second, update boot options
    update_payload = {
        "action": "update_boot_options",
        "mac": "de:ad:be:ef:00:01",
        "address": "minimal.local",
        "boot_options": ["ubuntu"],
    }
    resp = await client.post(webhook_url, json=update_payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    # Verify entities are created
    entity_id_switch = "switch.de_ad_be_ef_00_01_wake"
    entity_id_select = "select.de_ad_be_ef_00_01_next_boot_option"

    assert hass.states.get(entity_id_switch) is not None
    select_state = hass.states.get(entity_id_select)
    assert select_state is not None
    assert select_state.attributes.get("options") == [
        DEFAULT_BOOT_OPTION_NONE,
        "ubuntu",
    ]

    # Verify the switch works by calling turn_on
    with patch("custom_components.grubstation.switch.wakeonlan.send_magic_packet") as mock_wake:
        await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id_switch}, blocking=True)
        # With no broadcast args, it should be called with just the MAC
        mock_wake.assert_called_once_with("de:ad:be:ef:00:01", ip_address="255.255.255.255", port=9)


async def test_select_and_grub_config_view(hass: HomeAssistant, discovered_client) -> None:
    """Test selecting a boot option and retrieving the GRUB config view."""
    client = discovered_client
    entity_id_select = "select.aa_bb_cc_dd_ee_ff_next_boot_option"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id_select, "option": "ubuntu"},
        blocking=True,
    )

    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.state == "ubuntu"

    resp = await client.get("/api/grubstation/aa:bb:cc:dd:ee:ff?token=test_webhook_id")
    assert resp.status == HTTPStatus.OK
    text = await resp.text()
    assert "set default='ubuntu'" in text


async def test_switch_turn_on_does_not_reset_boot_option(hass: HomeAssistant, discovered_client) -> None:
    """Test that turning on the wake host switch sends magic packet and does not reset boot option."""
    entity_id_select = "select.aa_bb_cc_dd_ee_ff_next_boot_option"
    entity_id_switch = "switch.aa_bb_cc_dd_ee_ff_wake"

    # First, select a boot option
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id_select, "option": "windows"},
        blocking=True,
    )
    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.state == "windows"

    # Next, turn on the switch
    with patch("custom_components.grubstation.switch.wakeonlan.send_magic_packet") as mock_wake:
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": entity_id_switch},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_wake.assert_called_once_with("aa:bb:cc:dd:ee:ff")

    # Verify boot option does not reset to default
    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.state != DEFAULT_BOOT_OPTION_NONE


async def test_remove_integration_cleans_up(hass: HomeAssistant, discovered_client, mock_config_entry) -> None:
    """Test that removing the integration cleans up devices and entities."""
    entity_id_select = "select.aa_bb_cc_dd_ee_ff_next_boot_option"
    entity_id_switch = "switch.aa_bb_cc_dd_ee_ff_wake"

    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id_select) is None
    assert hass.states.get(entity_id_switch) is None

    er = async_get_er(hass)
    dr = async_get_dr(hass)
    assert er.async_get(entity_id_select) is None
    assert er.async_get(entity_id_switch) is None

    device = dr.async_get_device(identifiers={(DOMAIN, "aa:bb:cc:dd:ee:ff")})
    assert device is None


async def test_global_send_magic_packet_service(hass: HomeAssistant, setup_integration) -> None:
    """Test that the global send_turn_on_command service works."""
    with patch("custom_components.grubstation.wakeonlan.send_magic_packet") as mock_wake:
        await hass.services.async_call(
            DOMAIN,
            "send_turn_on_command",
            {
                "mac": "aa:bb:cc:dd:ee:ff",
                "broadcast_address": "192.168.1.255",
                "broadcast_port": 9,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_wake.assert_called_once_with("aa:bb:cc:dd:ee:ff", ip_address="192.168.1.255", port=9)


async def test_global_send_turn_off_command_service(hass: HomeAssistant, setup_integration) -> None:
    """Test that the global send_turn_off_command service works."""
    with patch(
        "custom_components.grubstation.async_send_turn_off_command",
        new_callable=AsyncMock,
    ) as mock_daemon_call:
        await hass.services.async_call(
            DOMAIN,
            "send_turn_off_command",
            {
                "address": "1.2.3.4",
                "daemon_port": 8081,
                "daemon_token": "secret",
            },
            blocking=True,
        )
        mock_daemon_call.assert_called_once_with(hass, "1.2.3.4", 8081, "secret")


async def test_webhook_validation_error(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns the error response from validation."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"

    resp = await client.post(webhook_url, data="not valid json")
    assert resp.status == HTTPStatus.BAD_REQUEST
    text = await resp.text()
    assert "Invalid JSON payload" in text


async def test_webhook_unexpected_empty_payload(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.INTERNAL_SERVER_ERROR if payload is unexpectedly None."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"

    with patch(
        "custom_components.grubstation.async_parse_webhook_request",
        return_value=(None, None),
    ):
        resp = await client.post(webhook_url, data="dummy")
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
        text = await resp.text()
        assert text == "Unexpected empty payload"


async def test_webhook_missing_action(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.BAD_REQUEST if action is missing from the validated payload."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"

    with patch(
        "custom_components.grubstation.async_parse_webhook_request",
        return_value=({"mac": "aa:bb:cc:dd:ee:ff"}, None),
    ):
        resp = await client.post(webhook_url, data="dummy")
        assert resp.status == HTTPStatus.BAD_REQUEST
        text = await resp.text()
        assert text == "Missing action in payload"


async def test_webhook_unknown_action(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.BAD_REQUEST for unknown action."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "unknown_action",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.BAD_REQUEST
    text = await resp.text()
    assert "Unknown action: unknown_action" in text


async def test_webhook_invalid_schema(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.BAD_REQUEST for invalid schema."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    # missing required 'address' or 'os' for register_daemon
    payload = {
        "action": "register_daemon_token",
        "mac": "aa:bb:cc:dd:ee:ff",
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.BAD_REQUEST
    text = await resp.text()
    assert "Invalid payload format" in text


async def test_webhook_register_daemon_token_existing_host(hass: HomeAssistant, setup_integration) -> None:
    """Test registering an already registered host."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "register_daemon_token",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
        "daemon_port": 8000,
        "daemon_token": "secret",
    }

    # First registration
    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK

    # Second registration (update)
    payload["address"] = "new.local"
    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()


async def test_webhook_update_boot_options_unregistered_host(hass: HomeAssistant, setup_integration) -> None:
    """Test updating boot options for a host that isn't registered creates entities."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "update_boot_options",
        "mac": "00:00:00:00:00:00",
        "address": "test.local",
        "boot_options": ["ubuntu"],
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    entity_id_select = "select.00_00_00_00_00_00_next_boot_option"
    state = hass.states.get(entity_id_select)
    assert state is not None
    assert state.attributes.get("options") == [DEFAULT_BOOT_OPTION_NONE, "ubuntu"]


async def test_global_send_magic_packet_service_minimal(hass: HomeAssistant, setup_integration) -> None:
    """Test that the global send_turn_on_command service works with minimal data."""
    with patch("custom_components.grubstation.wakeonlan.send_magic_packet") as mock_wake:
        await hass.services.async_call(
            DOMAIN,
            "send_turn_on_command",
            {
                "mac": "aa:bb:cc:dd:ee:ff",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_wake.assert_called_once_with("aa:bb:cc:dd:ee:ff", ip_address="255.255.255.255", port=9)


async def test_webhook_invalid_schema_update_boot_options(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.BAD_REQUEST for invalid schema in update_boot_options."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    # missing required 'boot_options'
    payload = {
        "action": "update_boot_options",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
    }

    resp = await client.post(webhook_url, json=payload)
    assert resp.status == HTTPStatus.BAD_REQUEST
    text = await resp.text()
    assert "Invalid payload format" in text


async def test_reload_entry(hass: HomeAssistant, setup_integration, mock_config_entry) -> None:
    """Test reloading the config entry."""
    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        # Trigger reload via the listener (simulated)
        await async_reload_entry(hass, mock_config_entry)
        mock_reload.assert_awaited_once_with(mock_config_entry.entry_id)


async def test_remove_config_entry_device_integration(
    hass: HomeAssistant, discovered_client, mock_config_entry
) -> None:
    """Test removing a device via the config entry."""
    dr = async_get_dr(hass)
    device = dr.async_get_device(identifiers={(DOMAIN, "aa:bb:cc:dd:ee:ff")})
    assert device is not None

    result = await async_remove_config_entry_device(hass, mock_config_entry, device)
    assert result is True
    assert "aa:bb:cc:dd:ee:ff" not in mock_config_entry.runtime_data.hosts


async def test_webhook_internal_server_error(hass: HomeAssistant, setup_integration) -> None:
    """Test webhook returns HTTPStatus.INTERNAL_SERVER_ERROR on unexpected exception."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    payload = {
        "action": "update_boot_options",
        "mac": "aa:bb:cc:dd:ee:ff",
        "address": "test.local",
        "boot_options": ["ubuntu", "windows"],
    }

    with patch(
        "custom_components.grubstation.manager.GrubStationManager.async_update_boot_options",
        side_effect=Exception("Boom"),
    ):
        resp = await client.post(webhook_url, json=payload)
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
        text = await resp.text()
        assert text == "Internal Server Error"

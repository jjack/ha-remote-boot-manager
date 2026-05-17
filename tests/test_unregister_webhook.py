"""Reproduction test for unregister_host webhook action."""
from http import HTTPStatus
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.grubstation.const import DOMAIN
from homeassistant.core import HomeAssistant
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

async def test_webhook_unregister_host(hass: HomeAssistant, setup_integration) -> None:
    """Test that the unregister_host action removes the host from Home Assistant."""
    client = setup_integration
    webhook_url = "/api/webhook/test_webhook_id"
    mac = "aa:bb:cc:dd:ee:ff"
    
    # 1. Register a host first
    payload_reg = {
        "action": "update_boot_options",
        "mac": mac,
        "address": "test.local",
        "boot_options": ["linux"],
    }
    resp = await client.post(webhook_url, json=payload_reg)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    # Verify host entry exists
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get("mac") == mac]
    assert len(entries) == 1

    # 2. Send unregister_host action
    payload_unreg = {
        "action": "unregister_host",
        "mac": mac,
        "address": "test.local", # Included because it's in BASE_SCHEMA
    }
    resp = await client.post(webhook_url, json=payload_unreg)
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()

    # BUG/Verify: Host entry should be gone
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get("mac") == mac]
    assert len(entries) == 0, "Host config entry should have been removed"

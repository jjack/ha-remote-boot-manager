"""Tests for GrubStation config flow."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation.const import DOMAIN
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Patch get_url to avoid NoURLAvailableError
    with patch("homeassistant.components.webhook.async_generate_url", return_value="http://hooks/test"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "webhook_info"

    with patch(
        "custom_components.grubstation.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "GrubStation"
    assert "webhook_id" in result["data"]
    assert len(mock_setup_entry.mock_calls) == 1


async def test_import(hass: HomeAssistant) -> None:
    """Test import step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_MAC: "00:11:22:33:44:55", "address": "test.local"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Host 00:11:22:33:44:55"
    assert result["data"][CONF_MAC] == "00:11:22:33:44:55"


async def test_options_flow_global(hass: HomeAssistant) -> None:
    """Test options flow for global entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="GrubStation",
        data={"webhook_id": "test_id"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "view_webhook"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "view_webhook"


async def test_form_already_configured(hass: HomeAssistant) -> None:
    """Test abort when already configured."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_invalid_data(hass: HomeAssistant) -> None:
    """Test import step with invalid data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={},
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "invalid_import_data"


async def test_reconfigure_flow(hass: HomeAssistant) -> None:
    """Test reconfigure flow."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    with patch("homeassistant.components.webhook.async_generate_url", return_value="http://hooks/test"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        # Based on implementation, async_init calls async_step_reconfigure
        # and if input is not None it calls async_step_reconfigure_webhook_info.
        # Actually, in the implementation:
        # if user_input is not None: ... return await self.async_step_reconfigure_webhook_info()
        # My test passes empty data={}, so async_step_reconfigure user_input is {}.
        # Wait, if I pass {}, user_input is NOT None.
        # So it proceeds to async_step_reconfigure_webhook_info.
        assert result["step_id"] == "reconfigure_webhook_info"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"done": True},
        )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_options_flow_init_global(hass: HomeAssistant) -> None:
    """Test options flow init for global entry without user input."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="GrubStation",
        data={"webhook_id": "test_id"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert "view_webhook" in result["menu_options"]

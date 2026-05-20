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


async def test_form_add_host_when_already_configured(hass: HomeAssistant) -> None:
    """Test showing add_host form when already configured."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_host"


async def test_add_host_flow(hass: HomeAssistant) -> None:
    """Test manual host addition flow."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MAC: "aa:bb:cc:dd:ee:ff",
            "address": "192.168.1.10",
            "boot_options": "Linux\nWindows",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Host aa:bb:cc:dd:ee:ff"
    assert result["data"][CONF_MAC] == "aa:bb:cc:dd:ee:ff"
    assert result["data"]["boot_options"] == ["Linux", "Windows"]


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
        # First step: show reconfigure form
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        # Second step: move to webhook info
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reconfigure_webhook_info"

        # Third step: complete
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"done": True},
        )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_missing_documentation(hass: HomeAssistant) -> None:
    """Test abortion when documentation is missing."""

    class MockIntegration:
        documentation = None

    with patch(
        "custom_components.grubstation.config_flow.async_get_loaded_integration",
        return_value=MockIntegration(),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "missing_documentation"


async def test_add_host_invalid_mac(hass: HomeAssistant) -> None:
    """Test add_host with invalid MAC address."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    # format_mac returns the input if it doesn't match 12 chars and has no hyphens.
    # But it might be that the validation expects something else.
    # In config_flow.py:
    # mac = format_mac(user_input[CONF_MAC])
    # if not mac: ...
    # Since format_mac("") returns "", this should trigger it.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MAC: "",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"][CONF_MAC] == "invalid_mac"


async def test_add_host_already_configured(hass: HomeAssistant) -> None:
    """Test add_host with already configured MAC."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    # The unique ID should match what format_mac returns
    mac = "aa:bb:cc:dd:ee:ff"
    MockConfigEntry(domain=DOMAIN, data={CONF_MAC: mac}, unique_id=mac).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MAC: mac,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_already_configured(hass: HomeAssistant) -> None:
    """Test import with already configured MAC."""
    mac = "aa:bb:cc:dd:ee:ff"
    MockConfigEntry(domain=DOMAIN, data={CONF_MAC: mac}, unique_id=mac).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_MAC: mac},
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_view_webhook_done(hass: HomeAssistant) -> None:
    """Test options flow view webhook completion."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="GrubStation",
        data={"webhook_id": "test_id"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "view_webhook"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"done": True},
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_options_flow_host(hass: HomeAssistant) -> None:
    """Test options flow for host entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MAC: "aa:bb:cc:dd:ee:ff", "boot_options": ["Linux"]},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "host_config"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "address": "1.2.3.4",
            "boot_options": "Linux\nWindows\n",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["address"] == "1.2.3.4"
    assert result["data"]["boot_options"] == ["Linux", "Windows"]


async def test_options_flow_host_no_boot_options(hass: HomeAssistant) -> None:
    """Test options flow for host entry with no boot options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MAC: "aa:bb:cc:dd:ee:ff"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "boot_options": "",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["boot_options"] == []


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

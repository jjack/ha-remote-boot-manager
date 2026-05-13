"""Test the config flow."""

import json
from unittest.mock import MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grubstation.config_flow import GrubStationManagerOptionsFlow
from custom_components.grubstation.const import DOMAIN
from custom_components.grubstation.data import RemoteHost
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {}

    with patch(
        "custom_components.grubstation.config_flow.webhook.async_generate_url",
        return_value="http://example.com/webhook",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("step_id") == "webhook_info"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {},
    )

    assert result3.get("type") == FlowResultType.CREATE_ENTRY
    assert result3.get("title") == "GrubStation"
    assert "webhook_id" in result3.get("data", {})


async def test_form_missing_documentation(hass: HomeAssistant) -> None:
    """Test we abort if documentation is missing."""
    with patch("custom_components.grubstation.config_flow.async_get_loaded_integration") as mock_get_integration:
        mock_integration = MagicMock()
        mock_integration.documentation = None
        mock_get_integration.return_value = mock_integration

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        assert result.get("type") == FlowResultType.ABORT
        assert result.get("reason") == "missing_documentation"


async def test_single_instance_allowed(hass: HomeAssistant) -> None:
    """Test that only a single instance is allowed."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"


async def test_reconfigure_flow(hass: HomeAssistant) -> None:
    """Test reconfigure flow to regenerate webhook ID."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "old_id"})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"

    with (
        patch(
            "custom_components.grubstation.config_flow.webhook.async_generate_id",
            return_value="new_id",
        ),
        patch(
            "custom_components.grubstation.config_flow.webhook.async_generate_url",
            return_value="http://example.com/new_webhook",
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("step_id") == "reconfigure_webhook_info"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={},
    )

    assert result3.get("type") == FlowResultType.ABORT
    assert result3.get("reason") == "reconfigure_successful"
    assert entry.data["webhook_id"] == "new_id"


async def test_options_flow_no_hosts(hass: HomeAssistant) -> None:
    """Test options flow shows the ID even when there are no hosts available."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    mock_manager = MagicMock()
    mock_manager.hosts = {}
    entry.runtime_data = mock_manager

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result.get("type") == FlowResultType.MENU
    assert result.get("step_id") == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "view_webhook"},
    )
    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("step_id") == "view_webhook"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={},
    )
    assert result3.get("type") == FlowResultType.CREATE_ENTRY
    assert result3.get("data") == {}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow to successfully configure a host script and addresses."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    mock_manager = MagicMock()
    mock_host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    mock_manager.hosts = {"00:11:22:33:44:55": mock_host}
    entry.runtime_data = mock_manager

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result.get("type") == FlowResultType.MENU
    assert result.get("step_id") == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "select_host"},
    )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("step_id") == "select_host"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={"host": "00:11:22:33:44:55"},
    )

    assert result3.get("type") == FlowResultType.FORM
    assert result3.get("step_id") == "host_config"

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        user_input={
            "turn_off_action": [{"action": "script.turn_off"}],
            "address": "new.local",
            "broadcast_address": "192.168.1.255",
            "broadcast_port": 9,
        },
    )

    assert result4.get("type") == FlowResultType.CREATE_ENTRY
    assert mock_host.off_action == [{"action": "script.turn_off"}]
    assert mock_host.address == "new.local"
    assert mock_host.broadcast_address == "192.168.1.255"
    assert mock_host.broadcast_port == 9
    mock_manager.save.assert_called_once()


async def test_options_flow_clear_script_and_service_fallback(
    hass: HomeAssistant,
) -> None:
    """Test options flow clearing a script and handling legacy 'service' action syntax."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    mock_manager = MagicMock()
    mock_host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
        off_action=[{"service": "script.turn_off"}],
    )
    mock_manager.hosts = {"00:11:22:33:44:55": mock_host}
    entry.runtime_data = mock_manager

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "select_host"},
    )

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={"host": "00:11:22:33:44:55"},
    )
    assert result3.get("type") == FlowResultType.FORM

    # Submit the form without specifying a turn_off_script to clear it
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        user_input={
            "address": "cleared.local",
        },
    )

    assert result4.get("type") == FlowResultType.CREATE_ENTRY
    assert mock_host.off_action is None
    assert mock_host.address == "cleared.local"
    mock_manager.save.assert_called()


async def test_options_flow_host_config_no_mac(hass: HomeAssistant) -> None:
    """Test options flow aborts if selected mac is missing."""
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.runtime_data = MagicMock()
    entry.add_to_hass(hass)

    flow = GrubStationManagerOptionsFlow(entry)
    flow.hass = hass

    result = await flow.async_step_host_config()
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "no_hosts"


async def test_options_flow_submit_without_host(hass: HomeAssistant) -> None:
    """Test the options flow select_host step when submitted without a host selection."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {"00:11:22:33:44:55": MagicMock()}
    mock_entry.runtime_data = mock_manager
    mock_entry.data = {"webhook_id": "test_id"}

    flow = GrubStationManagerOptionsFlow(mock_entry)
    flow.hass = hass

    # user_input is not None, but doesn't contain "host"
    result = await flow.async_step_select_host(user_input={})

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("data") == {}


async def test_options_flow_init_no_hosts_text(hass: HomeAssistant) -> None:
    """Test the options flow init step when no hosts have checked in yet."""
    mock_entry = MagicMock()
    mock_manager = MagicMock()
    mock_manager.hosts = {}
    mock_entry.runtime_data = mock_manager
    mock_entry.data = {"webhook_id": "test_id"}

    flow = GrubStationManagerOptionsFlow(mock_entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)

    assert result.get("type") == FlowResultType.MENU
    assert "No hosts have checked in yet" in (
        (result.get("description_placeholders") or {}).get("menu_description") or ""
    )


async def test_options_flow_serialization_safety(hass: HomeAssistant) -> None:
    """Test that the host config form schema is JSON serializable.

    This prevents 'Unknown error occurred' in the UI caused by vol.UNDEFINED.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={"webhook_id": "test_id"})
    entry.add_to_hass(hass)

    mock_manager = MagicMock()
    # Host with no off_action and some None fields to trigger vol.UNDEFINED previously
    mock_host = RemoteHost(
        mac="00:11:22:33:44:55",
        address=None,
        off_action=None,
    )
    mock_manager.hosts = {"00:11:22:33:44:55": mock_host}
    entry.runtime_data = mock_manager

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "select_host"},
    )
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={"host": "00:11:22:33:44:55"},
    )

    assert result3.get("type") == FlowResultType.FORM
    assert result3.get("step_id") == "host_config"

    schema = result3.get("data_schema")
    assert schema is not None

    descriptions = [key.description for key in schema.schema if hasattr(key, "description")]

    # This would raise TypeError if vol.UNDEFINED was present
    json_str = json.dumps(descriptions)
    assert "suggested_value" not in json_str

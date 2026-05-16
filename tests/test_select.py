"""Tests for GrubStation select platform."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.select import GrubStationManagerSelect, async_setup_entry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant


async def test_select_properties(hass):
    """Test select entity properties."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    host.boot_options = ["ubuntu", "windows"]
    host.next_boot_option = "ubuntu"
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host

    select = GrubStationManagerSelect(coordinator)

    assert select.unique_id == "00:11:22:33:44:55_boot_option_select"
    assert select.options == ["(none)", "ubuntu", "windows"]
    assert select.current_option == "ubuntu"


async def test_async_select_option(hass):
    """Test selecting an option."""
    host = RemoteHost(
        mac="00:11:22:33:44:55",
        address="test.local",
    )
    coordinator = MagicMock()
    coordinator.data = host
    coordinator.host = host
    coordinator.async_set_next_boot_option = AsyncMock()

    select = GrubStationManagerSelect(coordinator)

    await select.async_select_option("ubuntu")
    coordinator.async_set_next_boot_option.assert_called_once_with("ubuntu")


async def test_async_setup_entry(hass: HomeAssistant):
    """Test the setup entry logic."""
    mock_host = RemoteHost(mac="00:11:22:33:44:55")
    mock_coordinator = MagicMock()
    mock_coordinator.host = mock_host

    mock_entry = MagicMock()
    mock_entry.data = {CONF_MAC: "00:11:22:33:44:55"}
    mock_entry.runtime_data = mock_coordinator

    async_add_entities = MagicMock()

    await async_setup_entry(hass, mock_entry, async_add_entities)

    assert async_add_entities.call_count == 1
    added_entities = async_add_entities.call_args[0][0]
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], GrubStationManagerSelect)


async def test_async_setup_entry_global(hass: HomeAssistant):
    """Test setup entry for global entry."""
    mock_entry = MagicMock()
    mock_entry.data = {}
    async_add_entities = MagicMock()

    await async_setup_entry(hass, mock_entry, async_add_entities)
    async_add_entities.assert_not_called()

"""Test views for grubstation."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from aiohttp import web
from homeassistant.core import HomeAssistant

from custom_components.grubstation.const import DEFAULT_BOOT_OPTION_NONE
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.views import GrubConfigView


async def test_grub_config_view_invalid_mac(hass: HomeAssistant) -> None:
    """Test Invalid MAC (empty or falsy)."""
    view = GrubConfigView()
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}
    with patch("custom_components.grubstation.views.format_mac", return_value=""):
        resp = await view.get(mock_request, "invalid")
        assert resp.status == HTTPStatus.BAD_REQUEST
        assert resp.text == "Invalid MAC address format"


async def test_grub_config_view_host_not_found(hass: HomeAssistant) -> None:
    """Test host not found."""
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_manager = MagicMock()
    mock_manager.hosts = {}

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_manager
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    view = GrubConfigView()

    resp = await view.get(mock_request, "aa:bb:cc:dd:ee:ff")
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_grub_config_view_exception(hass: HomeAssistant) -> None:
    """Test exception generating config."""
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_manager = MagicMock()
    mock_manager.hosts = {
        "aa:bb:cc:dd:ee:ff": RemoteHost(
            mac="aa:bb:cc:dd:ee:ff",
            address="test.local",
            name="test",
        )
    }
    mock_manager.async_consume_next_boot_option.side_effect = Exception("Boom")

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_manager
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    view = GrubConfigView()

    resp = await view.get(mock_request, "aa:bb:cc:dd:ee:ff")
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_grub_config_view_success(hass: HomeAssistant) -> None:
    """Test successful request strictly consumes state and returns GRUB payload."""
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_entry = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    mock_manager = MagicMock()
    mock_manager.hosts = {
        "aa:bb:cc:dd:ee:ff": RemoteHost(
            mac="aa:bb:cc:dd:ee:ff",
            address="test.local",
            name="test",
            next_boot_option="windows",
        )
    }
    mock_manager.async_consume_next_boot_option.return_value = "windows"

    mock_entry.runtime_data = mock_manager
    view = GrubConfigView()

    resp = await view.get(mock_request, "aa:bb:cc:dd:ee:ff")
    assert resp.status == HTTPStatus.OK
    assert resp.text == "set default='windows'\n"
    mock_manager.async_consume_next_boot_option.assert_called_once_with(
        "aa:bb:cc:dd:ee:ff"
    )


async def test_grub_config_view_success_empty(hass: HomeAssistant) -> None:
    """Test successful request strictly consumes state and returns empty string."""
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_entry = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    mock_manager = MagicMock()
    mock_manager.hosts = {
        "aa:bb:cc:dd:ee:ff": RemoteHost(
            mac="aa:bb:cc:dd:ee:ff",
            address="test.local",
            name="test",
            next_boot_option=DEFAULT_BOOT_OPTION_NONE,
        )
    }
    mock_manager.async_consume_next_boot_option.return_value = DEFAULT_BOOT_OPTION_NONE

    mock_entry.runtime_data = mock_manager
    view = GrubConfigView()

    resp = await view.get(mock_request, "aa:bb:cc:dd:ee:ff")
    assert resp.status == HTTPStatus.OK
    assert resp.text == ""
    mock_manager.async_consume_next_boot_option.assert_called_once_with(
        "aa:bb:cc:dd:ee:ff"
    )


async def test_grub_config_view_integration_not_configured(hass: HomeAssistant) -> None:
    """Test that GrubConfigView handles missing config entries gracefully."""
    view = GrubConfigView()
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    with patch.object(hass.config_entries, "async_entries", return_value=[]):
        response = await view.get(mock_request, "00:11:22:33:44:55")

        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.text is not None
        assert response.text == "Integration not configured"


async def test_grub_config_view_integration_not_ready(hass: HomeAssistant) -> None:
    """Test that GrubConfigView handles integration not ready gracefully."""
    view = GrubConfigView()
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_entry = MagicMock()
    mock_entry.runtime_data = None
    with patch.object(hass.config_entries, "async_entries", return_value=[mock_entry]):
        response = await view.get(mock_request, "00:11:22:33:44:55")

        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.text is not None
        assert response.text == "Integration not ready"


async def test_grub_config_view_malformed_mac_error_path(hass: HomeAssistant) -> None:
    """Test the path of an invalid MAC address causing a ValueError in format_mac."""
    view = GrubConfigView()
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    with patch(
        "custom_components.grubstation.views.format_mac",
        side_effect=ValueError("Invalid MAC"),
    ):
        resp = await view.get(mock_request, "not-a-mac")
        assert resp.status == HTTPStatus.BAD_REQUEST
        assert resp.text == "Invalid MAC address format"


async def test_grub_config_view_escaping_quotes(hass: HomeAssistant) -> None:
    """Test that single quotes in boot options are escaped for GRUB."""
    mock_request = MagicMock(spec=web.Request)
    mock_request.app = {"hass": hass}

    mock_manager = MagicMock()
    # A boot option with a single quote that could break GRUB syntax if not escaped
    tricky_option = "Ubuntu 'Groggy' Edition"
    mock_manager.async_consume_next_boot_option.return_value = tricky_option

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_manager
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    view = GrubConfigView()

    resp = await view.get(mock_request, "aa:bb:cc:dd:ee:ff")
    assert resp.status == HTTPStatus.OK
    # Verify the quote is escaped with a backslash
    assert resp.text == "set default='Ubuntu \\'Groggy\\' Edition'\n"

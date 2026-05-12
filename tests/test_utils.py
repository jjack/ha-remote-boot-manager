"""Tests for GrubStation utilities."""

from custom_components.grubstation.const import DEFAULT_BROADCAST_ADDRESS
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.utils import generate_model_name


def test_generate_model_name_none():
    """Test generate_model_name with None host_data."""
    assert generate_model_name(None) == "Unknown Host"


def test_utils_generate_model_name_broadcast_port_only():
    """Test generate_model_name with only broadcast port set to non-default."""
    host = RemoteHost(
        mac="mac",
        os="linux",
        broadcast_address=DEFAULT_BROADCAST_ADDRESS,
        broadcast_port=123,
    )
    assert "Port: 123" in generate_model_name(host)

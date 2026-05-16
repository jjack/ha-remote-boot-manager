"""Tests for GrubStation utilities."""

from custom_components.grubstation.const import DEFAULT_BROADCAST_ADDRESS
from custom_components.grubstation.data import RemoteHost
from custom_components.grubstation.utils import generate_device_info, generate_model_name


def test_generate_model_name_none():
    """Test generate_model_name with None host_data."""
    assert generate_model_name(None) == "Unknown Host"


def test_utils_generate_model_name_broadcast_port_only():
    """Test generate_model_name with only broadcast port set to non-default."""
    host = RemoteHost(
        mac="mac",
        broadcast_address=DEFAULT_BROADCAST_ADDRESS,
        broadcast_port=123,
    )
    assert "Port: 123" in generate_model_name(host)


def test_utils_generate_model_name_full():
    """Test generate_model_name with full broadcast info."""
    host = RemoteHost(
        mac="mac",
        address="1.1.1.1",
        broadcast_address="1.1.1.255",
        broadcast_port=123,
    )
    model_name = generate_model_name(host)
    assert "1.1.1.1" in model_name
    assert "Broadcast: 1.1.1.255" in model_name
    assert "Port: 123" in model_name


def test_generate_device_info():
    """Test generate_device_info."""
    host = RemoteHost(
        mac="mac",
        os="linux",
        agent_service_manager="systemd",
        agent_version="1.0.0",
    )
    device_info = generate_device_info(host)
    assert device_info["model"] == "linux-systemd"
    assert device_info["sw_version"] == "1.0.0"

    # Test fallback to generate_model_name
    host_no_os = RemoteHost(mac="mac")
    device_info_no_os = generate_device_info(host_no_os)
    assert device_info_no_os["model"] == "GrubStation Host"

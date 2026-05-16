"""Tests for data models."""

from custom_components.grubstation.const import DEFAULT_BOOT_OPTION_NONE
from custom_components.grubstation.data import RemoteHost


def test_remote_host_formatted_boot_options():
    """Test formatted_boot_options property."""
    # Test empty boot options
    host = RemoteHost(mac="AA:BB:CC:DD:EE:FF")
    assert host.formatted_boot_options == [DEFAULT_BOOT_OPTION_NONE]

    # Test existing boot options
    host.boot_options = ["a", "b"]
    assert host.formatted_boot_options == [DEFAULT_BOOT_OPTION_NONE, "a", "b"]

    # Test boot options already including default
    host.boot_options = [DEFAULT_BOOT_OPTION_NONE, "c"]
    assert host.formatted_boot_options == [DEFAULT_BOOT_OPTION_NONE, "c"]


def test_remote_host_update_from_payload():
    """Test update_from_payload method."""
    host = RemoteHost(mac="AA:BB:CC:DD:EE:FF")
    payload = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "action": "update",
        "address": "1.1.1.1",
        "agent_port": 1234,
        "agent_token": "token",
    }
    host.update_from_payload(payload)
    assert host.address == "1.1.1.1"
    assert host.agent_port == 1234
    assert host.agent_token == "token"


def test_remote_host_agent_is_configured():
    """Test agent_is_configured method."""
    host = RemoteHost(mac="AA:BB:CC:DD:EE:FF")
    assert not host.agent_is_configured()

    host.address = "1.1.1.1"
    host.agent_port = 1234
    host.agent_token = "token"
    assert host.agent_is_configured()

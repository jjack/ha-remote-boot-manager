"""Utility functions for GrubStation."""

from typing import TYPE_CHECKING

from custom_components.grubstation.const import DEFAULT_BROADCAST_ADDRESS, DEFAULT_BROADCAST_PORT, DOMAIN
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo

if TYPE_CHECKING:
    from .data import RemoteHost


def generate_device_info(host: RemoteHost) -> DeviceInfo:
    """Generate a DeviceInfo object with common values for all the platforms."""
    return DeviceInfo(
        identifiers={(DOMAIN, host.mac)},
        name=host.mac,
        manufacturer="GrubStation",
        model=generate_model_name(host),
        sw_version=host.daemon_version,
        connections={(CONNECTION_NETWORK_MAC, host.mac)},
    )


def generate_model_name(host: RemoteHost | None) -> str:
    """Generate a model name string for device info."""
    if host is None:
        return "Unknown Host"

    broadcast_info = []
    if host.broadcast_address and host.broadcast_address != DEFAULT_BROADCAST_ADDRESS:
        broadcast_info.append(f"Broadcast: {host.broadcast_address}")
    if host.broadcast_port and host.broadcast_port != DEFAULT_BROADCAST_PORT:
        broadcast_info.append(f"Port: {host.broadcast_port}")

    model_name = "GrubStation Host"
    if host.address:
        model_name = host.address

    if broadcast_info:
        model_name = f"{model_name} ({', '.join(broadcast_info)})"

    return model_name

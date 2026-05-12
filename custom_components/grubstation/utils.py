"""Utility functions for GrubStation."""

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo

from custom_components.grubstation.const import (
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DOMAIN,
)

if TYPE_CHECKING:
    from .data import RemoteHost


def generate_device_info(host_data: RemoteHost) -> DeviceInfo:
    """Generate a DeviceInfo object with common values for all the platforms."""
    return DeviceInfo(
        identifiers={(DOMAIN, host_data.mac)},
        name=host_data.mac,
        manufacturer="GrubStation",
        model=generate_model_name(host_data),
        sw_version=host_data.daemon_version,
        connections={(CONNECTION_NETWORK_MAC, host_data.mac)},
    )


def generate_model_name(host_data: RemoteHost | None) -> str:
    """Generate a model name string for device info."""
    if host_data is None:
        return "Unknown Host"

    broadcast_info = []
    if (
        host_data.broadcast_address
        and host_data.broadcast_address != DEFAULT_BROADCAST_ADDRESS
    ):
        broadcast_info.append(f"Broadcast: {host_data.broadcast_address}")
    if host_data.broadcast_port and host_data.broadcast_port != DEFAULT_BROADCAST_PORT:
        broadcast_info.append(f"Port: {host_data.broadcast_port}")

    model_name = f"{host_data.os}"
    if host_data.daemon_service_manager:
        model_name = f"{model_name}-{host_data.daemon_service_manager}"

    if broadcast_info:
        model_name = f"{model_name} ({', '.join(broadcast_info)})"

    return model_name

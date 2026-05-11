"""Utility functions for GrubStation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data import RemoteHost


def generate_model_name(host_data: RemoteHost) -> str:
    """Generate a model name string for device info."""
    broadcast_info = []
    if host_data.broadcast_address:
        broadcast_info.append(f"Broadcast: {host_data.broadcast_address}")
    if host_data.broadcast_port:
        broadcast_info.append(f"Port: {host_data.broadcast_port}")

    model_name = "Wake-on-LAN"
    if broadcast_info:
        model_name = f"{model_name} ({', '.join(broadcast_info)})"

    if host_data.os and host_data.service_manager:
        model_name = f"{host_data.os}-{host_data.service_manager} {model_name}"

    return model_name

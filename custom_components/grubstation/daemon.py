"""Interface to a simple GO daemon that talks to the GruBStation demon."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiohttp
from yarl import URL

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# send a POST request to the entry's address with the daemon port to /shutdown
# include the api_key as a "Bearer" token
async def async_send_turn_off_command(hass: HomeAssistant, address: str, daemon_port: int, api_key: str) -> None:
    """Send shutdown command to the GrubStation daemon."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=daemon_port, path="/shutdown")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with asyncio.timeout(5):
            async with session.post(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                if data.get("status") == "error":
                    raise HomeAssistantError(data.get("error", "Unknown error from daemon"))
    except Exception as err:
        if isinstance(err, HomeAssistantError):
            raise
        if not isinstance(err, (aiohttp.ClientError, asyncio.TimeoutError)):
            LOGGER.exception("Unexpected error sending shutdown command to %s", address)
        error_msg = f"Shutdown command failed: {err}"
        raise HomeAssistantError(error_msg) from err


async def async_get_daemon_status(
    hass: HomeAssistant, address: str, daemon_port: int, api_key: str
) -> dict[str, str] | None:
    """Get the status and metadata from the GrubStation daemon."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=daemon_port, path="/status")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with asyncio.timeout(5):
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                LOGGER.debug("Got daemon status: %s", data)
                return {
                    "os": data.get("os"),
                    "service_manager": data.get("service_manager"),
                    "version": data.get("version"),
                }
    except Exception as err:  # noqa: BLE001
        LOGGER.debug("Daemon status check failed for %s: %s", address, err)
        return None

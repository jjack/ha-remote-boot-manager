"""A simple agent for telling the GRUB OS Selector daemon to turn off."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# send a POST request to the entry's address with the agent port to /shutdown
# include the api_key as a "Bearer" token
async def async_send_turn_off_command(
    hass: HomeAssistant, address: str, agent_port: int, api_key: str
) -> None:
    """Send shutdown command to the GRUB OS Selector agent."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=agent_port, path="/shutdown")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with asyncio.timeout(5):
            async with session.post(url, headers=headers) as response:
                response.raise_for_status()
    except Exception as err:
        if not isinstance(err, (aiohttp.ClientError, asyncio.TimeoutError)):
            LOGGER.exception("Unexpected error sending shutdown command to %s", address)
        error_msg = f"Shutdown command failed: {err}"
        raise HomeAssistantError(error_msg) from err


async def async_check_agent_status(
    hass: HomeAssistant, address: str, agent_port: int, api_key: str
) -> bool:
    """Check if the GRUB OS Selector agent is accessible."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=agent_port, path="/healthcheck")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with asyncio.timeout(5):
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("status") == "ok"
    except Exception:  # noqa: BLE001
        # We don't need to log every failure since it's polled regularly
        return False

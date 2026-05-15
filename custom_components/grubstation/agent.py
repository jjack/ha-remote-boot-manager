"""Interface to a simple GO agent that talks to the GruBStation demon."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import aiohttp
import voluptuous as vol
from yarl import URL

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import API_KEY_OS, API_KEY_SERVICE_MANAGER, API_KEY_STATUS, API_KEY_VERSION, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

AGENT_STATUS_SCHEMA = vol.Schema(
    {
        vol.Required(API_KEY_STATUS): cv.string,
        vol.Required(API_KEY_OS): cv.string,
        vol.Required(API_KEY_SERVICE_MANAGER): cv.string,
        vol.Required(API_KEY_VERSION): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_send_turn_off_command(hass: HomeAssistant, address: str, agent_port: int, api_key: str) -> None:
    """Send shutdown command to the GrubStation agent."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=agent_port, path="/shutdown")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with asyncio.timeout(5):
            async with session.post(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
    except Exception as err:
        if not isinstance(err, (aiohttp.ClientError, asyncio.TimeoutError)):
            LOGGER.exception("Unexpected error sending shutdown command to %s", address)
        raise HomeAssistantError(f"Shutdown command failed: {err}") from err

    if data.get("status") == "error":
        raise HomeAssistantError(data.get("error", "Unknown error from agent"))


async def async_get_agent_status(hass: HomeAssistant, address: str, agent_port: int, api_key: str) -> dict[str, str]:
    """Get the status and metadata from the GrubStation agent."""
    session = async_get_clientsession(hass)
    url = URL.build(scheme="http", host=address, port=agent_port, path="/status")
    headers = {"Authorization": f"Bearer {api_key}"}

    async with asyncio.timeout(5):
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            return cast(dict[str, str], AGENT_STATUS_SCHEMA(data))

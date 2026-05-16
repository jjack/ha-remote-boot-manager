"""Sensor platform for GrubStation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
)
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Only set up if this is a per-host entry
    if not entry.data.get(CONF_MAC):
        return

    coordinator = entry.runtime_data
    if coordinator.host.agent_is_configured():
        async_add_entities([GrubStationManagerSensor(coordinator)])


class GrubStationManagerSensor(CoordinatorEntity, SensorEntity):
    """GrubStation sensor class."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.host = coordinator.host

        self._attr_unique_id = f"{self.host.mac}_last_agent_accessible"
        self._attr_translation_key = "last_agent_accessible"
        self._attr_icon = "mdi:heart-pulse"
        self._attr_device_info = generate_device_info(self.host)

    @property
    def native_value(self) -> str | None:
        """Return the value of the sensor."""
        return self.coordinator.data.last_agent_accessible

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        host = self.coordinator.data
        return {
            ATTR_AGENT_STATUS: host.agent_status,
            ATTR_HOST_OS: host.os,
            ATTR_AGENT_SERVICE_MANAGER: host.agent_service_manager,
            ATTR_AGENT_VERSION: host.agent_version,
        }

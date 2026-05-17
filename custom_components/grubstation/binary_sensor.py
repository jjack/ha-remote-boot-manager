"""Binary sensor platform for GrubStation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AGENT_SERVICE_MANAGER,
    ATTR_AGENT_STATUS,
    ATTR_AGENT_VERSION,
    ATTR_HOST_OS,
    ATTR_LAST_AGENT_ACCESSIBLE,
)
from .utils import generate_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GrubStationManagerConfigEntry


@dataclass(frozen=True, kw_only=True)
class GrubStationBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a GrubStation binary sensor."""


BINARY_SENSOR_DESCRIPTIONS = (
    GrubStationBinarySensorEntityDescription(
        key="health_status",
        translation_key="agent_status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrubStationManagerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    # Only set up if this is a per-host entry
    if not entry.data.get(CONF_MAC):
        return

    coordinator = entry.runtime_data
    async_add_entities(
        [GrubStationManagerBinarySensor(coordinator, description) for description in BINARY_SENSOR_DESCRIPTIONS]
    )


class GrubStationManagerBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """GrubStation binary sensor class."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: Any, description: GrubStationBinarySensorEntityDescription) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.host = coordinator.host

        self._attr_unique_id = f"{self.host.mac}_{description.key}"
        self._attr_device_info = generate_device_info(self.host)

    @property
    def is_on(self) -> bool:
        """Return true if the agent is accessible."""
        return self.coordinator.data.is_agent_accessible

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        host = self.coordinator.data
        return {
            ATTR_LAST_AGENT_ACCESSIBLE: host.last_agent_accessible,
            ATTR_AGENT_STATUS: host.agent_status,
            ATTR_HOST_OS: host.os,
            ATTR_AGENT_SERVICE_MANAGER: host.agent_service_manager,
            ATTR_AGENT_VERSION: host.agent_version,
        }

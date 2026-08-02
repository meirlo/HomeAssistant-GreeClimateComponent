"""Base entity for Gree integration."""

from __future__ import annotations

# Standard library imports
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Home Assistant imports
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo, Entity

# Local imports
from .const import DOMAIN


@dataclass
class GreeEntityDescription:
    """Describes Gree entity."""

    property_key: str
    """Fills key and translation_key."""
    key: str = None
    translation_key: str = None

    def __post_init__(self):
        self.key = self.property_key
        self.translation_key = self.property_key

    name: str = None
    icon: str = None
    entity_category: str = None
    exists_fn: Callable[[object, object], bool] = lambda description, device: True
    value_fn: Callable[[object], Any] = None
    available_fn: Callable[[object], bool] = lambda device: True
    icon_fn: Callable[[Any, object], str] = None


class GreeEntity(Entity):
    """Base Gree entity."""

    _attr_has_entity_name = True
    entity_description: GreeEntityDescription

    def __init__(self, hass, entry, description: GreeEntityDescription) -> None:
        """Initialize Gree entity."""
        # Get the device from the entry data
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        self._device = entry_data.get("device")
        self.entity_description = description
        self._set_id()

    @property
    def _device_id(self) -> str:
        """Return the per-unit identifier for this entity's device.

        VRF gateways share a single gateway MAC (``_mac_addr``) across all of
        their indoor units. Using it here would make every unit share the same
        unique_id (causing entities like the external temperature sensor select
        to collide/be shared) and collapse all units into one HA device.
        ``_sub_mac_addr`` is unique per unit; for standalone devices it equals
        ``_mac_addr`` so behaviour is unchanged.
        """
        return getattr(self._device, "_sub_mac_addr", self._device._mac_addr)

    def _set_id(self) -> None:
        """Set entity ID and unique ID."""
        if self.entity_description:
            if self.entity_description.icon_fn is not None:
                self._attr_icon = self.entity_description.icon_fn(self.native_value, self._device)
            elif self.entity_description.icon is not None:
                self._attr_icon = self.entity_description.icon

            self._attr_unique_id = f"{self._device_id}_{self.entity_description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device._name,
            manufacturer="Gree",
            connections={(CONNECTION_NETWORK_MAC, self._device._sub_mac_addr)}
            if getattr(self._device, "_sub_mac_addr", None) == self._device._mac_addr
            else set(),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(self._device)
        return self._device._device_online if hasattr(self._device, "_device_online") else True

    @property
    def native_value(self) -> Any:
        """Return the native value of the entity."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self._device)
        return None

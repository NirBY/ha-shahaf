"""Manual refresh through the shared coordinator."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .entity import ShahafEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ShahafRefreshButton(entry.runtime_data, "refresh")])


class ShahafRefreshButton(ShahafEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:refresh"

    async def async_press(self):
        await self.coordinator.async_request_refresh()

"""Common class identity and freshness metadata."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CAMPUS_CODE, CONF_CLASS_ID, CONF_CLASS_NAME, CONF_SCHOOL_ID, DOMAIN
from .coordinator import ShahafCoordinator


class ShahafEntity(CoordinatorEntity[ShahafCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        entry = coordinator.entry
        identity = ":".join(
            str(entry.data[key]) for key in (CONF_SCHOOL_ID, CONF_CAMPUS_CODE, CONF_CLASS_ID)
        )
        self._attr_unique_id = f"{identity}:{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity)},
            name=f"Shahaf {entry.title}",
            manufacturer="Shahaf",
            model="Class timetable",
        )

    @property
    def extra_state_attributes(self):
        data = self.coordinator.entry.data
        return {
            "school_id": data[CONF_SCHOOL_ID],
            "campus_code": data[CONF_CAMPUS_CODE],
            "class_id": data[CONF_CLASS_ID],
            "class_name": data[CONF_CLASS_NAME],
            "data_stale": not self.coordinator.last_update_success,
            "last_update": self.coordinator.data["fetched_at"],
            "source_updated_at": self.coordinator.data["source_updated_at"],
            "scope": "class",
            "schema_version": 1,
        }

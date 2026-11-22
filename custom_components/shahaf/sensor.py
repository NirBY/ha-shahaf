"""Published timetable and dated notices for dashboards and automations."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory

from .entity import ShahafEntity
from .model import TZ, compact_schedule

KEYS = ("timetable", "today", "tomorrow", "changes", "exams", "events", "notices", "last_refresh")


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ShahafSensor(entry.runtime_data, key) for key in KEYS)


class ShahafSensor(ShahafEntity, SensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_icon = (
            "mdi:timetable" if key in ("timetable", "today", "tomorrow") else "mdi:calendar-text"
        )
        if key == "last_refresh":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _day(self):
        day = datetime.now(TZ).date() + timedelta(days=int(self.key == "tomorrow"))
        return next(
            (d for d in self.coordinator.data["days"] if d["date"] == day.isoformat()), None
        )

    @property
    def native_value(self):
        data = self.coordinator.data
        if self.key == "last_refresh":
            return datetime.fromisoformat(data["fetched_at"])
        if self.key in ("today", "tomorrow"):
            day = self._day()
            return len(day["lessons"]) if day is not None else None
        if self.key == "timetable":
            return sum(len(day["lessons"]) for day in data["days"])
        return len(data[self.key])

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        data = self.coordinator.data
        if self.key == "timetable":
            attrs["schedule"] = compact_schedule(data["days"])
            attrs["coverage_start"] = min(day["date"] for day in data["days"])
            attrs["coverage_end"] = max(day["date"] for day in data["days"])
        elif self.key in ("today", "tomorrow"):
            day = self._day()
            attrs["date"] = (
                datetime.now(TZ).date() + timedelta(days=int(self.key == "tomorrow"))
            ).isoformat()
            attrs["published"] = day is not None
            attrs["lessons"] = day["lessons"] if day else []
        elif self.key != "last_refresh":
            attrs["items"] = data[self.key]
        return attrs

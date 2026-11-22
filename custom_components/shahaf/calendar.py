"""Read-only calendars containing only dates actually published by the school."""

from datetime import date, datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent

from .entity import ShahafEntity
from .model import TZ


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            ShahafCalendar(entry.runtime_data, "lessons"),
            ShahafCalendar(entry.runtime_data, "school_events"),
        ]
    )


def _as_datetime(value):
    return value if isinstance(value, datetime) else datetime.combine(value, time.min, TZ)


class ShahafCalendar(ShahafEntity, CalendarEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key

    def _events(self):
        result = []
        if self.key == "lessons":
            for day in self.coordinator.data["days"]:
                for slot in day["lessons"]:
                    if slot["start"] and slot["end"]:
                        result.append(
                            CalendarEvent(
                                start=datetime.fromisoformat(slot["start"]),
                                end=datetime.fromisoformat(slot["end"]),
                                summary=f"{slot['lesson']}: {slot['subject']}",
                                description="\n".join(slot["details"]),
                            )
                        )
        else:
            seen = set()
            for item in self.coordinator.data["exams"] + self.coordinator.data["events"]:
                identity = (item["date"], item["text"])
                if not item["date"] or identity in seen:
                    continue
                seen.add(identity)
                start = date.fromisoformat(item["date"])
                result.append(
                    CalendarEvent(
                        start=start,
                        end=start + timedelta(days=1),
                        summary=item["text"].splitlines()[0],
                        description=item["text"],
                    )
                )
        return sorted(result, key=lambda event: _as_datetime(event.start))

    @property
    def event(self):
        now = datetime.now(TZ)
        return next((e for e in self._events() if _as_datetime(e.end) > now), None)

    async def async_get_events(self, hass, start_date, end_date):
        return [
            e
            for e in self._events()
            if _as_datetime(e.start) < end_date and _as_datetime(e.end) > start_date
        ]

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
            ShahafCalendar(entry.runtime_data, "changes"),
            ShahafCalendar(entry.runtime_data, "all_data"),
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
        if self.key in ("lessons", "all_data"):
            for day in self.coordinator.data["days"]:
                for slot in day["lessons"]:
                    if self.key == "all_data" and not (slot["start"] and slot["end"]):
                        start = date.fromisoformat(day["date"])
                        result.append(
                            CalendarEvent(
                                start=start,
                                end=start + timedelta(days=1),
                                summary=f"{slot['lesson']}: {slot['subject']}",
                                description="Bell times not published\n"
                                + "\n".join(slot["details"]),
                            )
                        )
                    if slot["start"] and slot["end"]:
                        result.append(
                            CalendarEvent(
                                start=datetime.fromisoformat(slot["start"]),
                                end=datetime.fromisoformat(slot["end"]),
                                summary=f"{slot['lesson']}: {slot['subject']}",
                                description="\n".join(slot["details"]),
                            )
                        )
        if self.key in ("school_events", "changes", "all_data"):
            seen = set()
            categories = (
                ("exams", "events", "changes", "notices")
                if self.key == "all_data"
                else (("changes",) if self.key == "changes" else ("exams", "events"))
            )
            items = [
                (category, item)
                for category in categories
                for item in self.coordinator.data[category]
            ]
            for category, item in items:
                identity = (item["date"], item.get("heading"), item["text"])
                if not item["date"] or identity in seen:
                    continue
                seen.add(identity)
                start = date.fromisoformat(item["date"])
                result.append(
                    CalendarEvent(
                        start=start,
                        end=start + timedelta(days=1),
                        summary=(
                            " · ".join(
                                filter(None, [item.get("heading"), *item["text"].splitlines()])
                            )
                            if self.key == "changes"
                            else f"{category}: {item['text'].splitlines()[0]}"
                        ),
                        description="\n".join(filter(None, [item.get("heading"), item["text"]])),
                    )
                )
        if self.key == "all_data":
            undated = [
                item["text"]
                for key in ("changes", "exams", "events", "notices")
                for item in self.coordinator.data[key]
                if not item.get("date")
            ]
            if undated:
                for event in result:
                    event.description = (
                        (event.description or "")
                        + "\n\nUndated school notices:\n"
                        + "\n".join(dict.fromkeys(undated))
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

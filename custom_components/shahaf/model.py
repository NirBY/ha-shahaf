"""Normalize the app's presentation JSON without guessing student group membership."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .api import ShahafError
from .const import SCHOOL_TIME_ZONE

TZ = ZoneInfo(SCHOOL_TIME_ZONE)
MONTHS = {
    "ינואר": 1,
    "פברואר": 2,
    "מרץ": 3,
    "מרס": 3,
    "אפריל": 4,
    "מאי": 5,
    "יוני": 6,
    "יולי": 7,
    "אוגוסט": 8,
    "ספטמבר": 9,
    "אוקטובר": 10,
    "נובמבר": 11,
    "דצמבר": 12,
}


def sunday(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def text_parts(elements: Any) -> list[str]:
    if elements is None:
        return []
    if not isinstance(elements, list):
        raise ShahafError("Unsupported text format")
    return [
        str(e["t"]).replace("\xa0", " ").strip()
        for e in elements
        if isinstance(e, dict) and e.get("t") is not None and str(e["t"]).strip()
    ]


def nearby_date(month: int, day: int, reference: date) -> date:
    candidates = []
    for year in range(reference.year - 1, reference.year + 2):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    if not candidates:
        raise ShahafError("Invalid date in timetable")
    return min(candidates, key=lambda value: abs((value - reference).days))


def hebrew_date(text: str, reference: date) -> date | None:
    for month_name, month in MONTHS.items():
        match = re.search(rf"(\d{{1,2}})\s+{month_name}(?:\s+(\d{{4}}))?", text)
        if match:
            try:
                return (
                    date(int(match[2]), month, int(match[1]))
                    if match[2]
                    else nearby_date(month, int(match[1]), reference)
                )
            except ValueError:
                raise ShahafError("Invalid notice date") from None
    return None


def _week_start(view: dict, requested: date) -> date:
    """Navigation carries the year; section keys only contain MMDD."""
    toolbar = view.get("tb") or {}
    starts = []
    for direction, shift in (("l", -7), ("r", 7)):
        value = (toolbar.get(direction) or {}).get("date")
        if value:
            try:
                starts.append(datetime.strptime(value, "%Y%m%d").date() + timedelta(days=shift))
            except (ValueError, TypeError):
                raise ShahafError("Invalid timetable navigation") from None
    if starts and any(start != starts[0] for start in starts):
        raise ShahafError("Inconsistent timetable dates")
    start = starts[0] if starts else sunday(requested)
    if start != sunday(requested):
        raise ShahafError("Shahaf returned a different week")
    return start


def _slot(row: dict, day: date) -> dict | None:
    details = text_parts(row.get("i"))
    if not details:
        return None
    header = text_parts(row.get("h"))
    # Footer and other non-lesson rows must not turn into calendar events.
    if not header or not header[0].isdigit():
        raise ShahafError("Unrecognized timetable row")
    clocks = [value for value in header[1:] if re.fullmatch(r"\d{1,2}:\d{2}", value)]
    start = end = None
    if len(clocks) >= 2:
        try:
            start = datetime.combine(day, time.fromisoformat(clocks[0].zfill(5)), TZ)
            end = datetime.combine(day, time.fromisoformat(clocks[1].zfill(5)), TZ)
        except ValueError:
            raise ShahafError("Invalid lesson time") from None
        if end <= start:
            raise ShahafError("Lesson end is not after its start")
    subjects = []
    for item in row.get("i") or []:
        style = item.get("s") or {}
        fields = str(style.get("s", "")).split(":")
        if style.get("textStyle") == "bold" or (len(fields) > 5 and fields[5] == "bold"):
            value = str(item.get("t") or "").strip()
            if value and value not in subjects:
                subjects.append(value)
    return {
        "lesson": int(header[0]),
        "subjects": subjects,
        "subject": " / ".join(subjects) or details[0],
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "details": details,
    }


def parse_week(payload: dict, requested: date) -> dict[str, Any]:
    """Keep explicit dates and notes. Do not repeat lessons beyond returned dates."""
    views = payload.get("views")
    if not isinstance(views, list):
        raise ShahafError("Missing app views")
    timetable = next((v for v in views if v.get("t") == "מערכת"), None)
    if timetable is None or not timetable.get("d"):
        raise ShahafError("No supported timetable view was returned")
    start = _week_start(timetable, requested)
    dates = {
        (start + timedelta(days=i)).strftime("%m%d"): start + timedelta(days=i) for i in range(7)
    }
    days = []
    for section in timetable["d"]:
        day = dates.get(section.get("k"))
        if day is None or not isinstance(section.get("r"), list):
            raise ShahafError("Unrecognized timetable day")
        lessons = [slot for row in section["r"] if (slot := _slot(row, day)) is not None]
        days.append(
            {"date": day.isoformat(), "day": (day.weekday() + 1) % 7 + 1, "lessons": lessons}
        )
    result: dict[str, Any] = {
        "days": sorted(days, key=lambda d: d["date"]),
        "changes": [],
        "exams": [],
        "events": [],
        "notices": [],
        "source_updated_at": None,
    }
    categories = {"שינויים": "changes", "מבחנים": "exams", "אירועים": "events"}
    for view in views:
        if view is timetable:
            continue
        category = categories.get(view.get("t"), "notices")
        context_date = None
        for section in view.get("d") or []:
            for row in section.get("r") or []:
                header = text_parts(row.get("h"))
                details = text_parts(row.get("i"))
                heading = " ".join(header)
                updated = re.search(r"מעודכן לתאריך (\d{2}/\d{2}/\d{4}) שעה (\d{2}:\d{2})", heading)
                if updated:
                    result["source_updated_at"] = (
                        datetime.strptime(" ".join(updated.groups()), "%d/%m/%Y %H:%M")
                        .replace(tzinfo=TZ)
                        .isoformat()
                    )
                    continue
                row_date = hebrew_date(heading, start)
                if row_date:
                    context_date = row_date
                if not details:
                    continue
                result[category].append(
                    {
                        "date": context_date.isoformat() if context_date else None,
                        "heading": heading,
                        "text": "\n".join(details),
                    }
                )
    return result


def combine_weeks(first: dict, second: dict) -> dict:
    """Use only the current response's notices; merge the two dated timetables."""
    dates = {day["date"]: day for day in first["days"] + second["days"]}
    return {**first, "days": [dates[key] for key in sorted(dates)]}


def compact_schedule(days: list[dict]) -> list[dict]:
    """Stable dated contract for consumers such as the future Mashov integration."""
    return [
        {
            **day,
            "lessons": [
                {key: slot[key] for key in ("lesson", "subject", "start", "end")}
                for slot in day["lessons"]
            ],
        }
        for day in days
    ]

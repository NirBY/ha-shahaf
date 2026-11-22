from datetime import date

import pytest

from custom_components.shahaf.api import ShahafError
from custom_components.shahaf.model import hebrew_date, parse_week, sunday
from tests.conftest import week_payload


def test_preserves_parallel_groups_and_notes():
    data = parse_week(week_payload(date(2026, 11, 22)), date(2026, 11, 22))
    slot = data["days"][0]["lessons"][0]
    assert slot["subjects"] == ["Math", "English"]
    assert "Teacher B" in slot["details"]
    assert slot["start"] == "2026-11-22T08:30:00+02:00"
    assert len(data["days"][0]["lessons"]) == 1  # Empty period is not a lesson.
    assert data["changes"][0]["date"] == "2026-11-22"
    assert data["events"][0]["date"] == "2026-11-26"
    assert data["exams"] == []
    assert data["source_updated_at"] == "2026-11-22T06:45:00+02:00"


def test_december_january_and_israel_summer_time():
    assert hebrew_date("יום ה 1 ינואר", date(2025, 12, 28)) == date(2026, 1, 1)
    assert hebrew_date("יום ה 31 דצמבר", date(2027, 1, 3)) == date(2026, 12, 31)
    week = sunday(date(2026, 7, 12))
    data = parse_week(week_payload(week), week)
    assert data["days"][0]["lessons"][0]["start"].endswith("+03:00")


def test_rejects_missing_or_wrong_week():
    with pytest.raises(ShahafError):
        parse_week({"views": []}, date(2026, 11, 22))
    with pytest.raises(ShahafError):
        parse_week(week_payload(date(2026, 11, 22)), date(2026, 11, 29))


def test_missing_bell_time_is_not_invented():
    week = date(2026, 11, 22)
    payload = week_payload(week)
    payload["views"][0]["d"][0]["r"][0]["h"] = [{"t": "1"}]
    slot = parse_week(payload, week)["days"][0]["lessons"][0]
    assert slot["start"] is None and slot["end"] is None


def test_empty_published_day_is_valid():
    week = date(2026, 11, 22)
    payload = week_payload(week)
    payload["views"][0]["d"][0]["r"] = []
    assert parse_week(payload, week)["days"] == [{"date": "2026-11-22", "day": 1, "lessons": []}]

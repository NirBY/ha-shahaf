from copy import deepcopy

from custom_components.shahaf.model import notice_time_range

DAYS = [
    {
        "date": "2026-11-23",
        "lessons": [
            {"lesson": 3, "start": "2026-11-23T10:00:00+02:00", "end": "2026-11-23T10:45:00+02:00"},
            {"lesson": 4, "start": "2026-11-23T11:00:00+02:00", "end": "2026-11-23T11:45:00+02:00"},
        ],
    }
]


def test_exact_range_and_teacher_assignment_lines():
    item = {
        "date": "2026-11-23",
        "heading": "",
        "text": "English exam\nשעורים 3 - 4\nשעור 3   Teacher A\nשעור 4   Teacher B",
    }
    start, end = notice_time_range(item, DAYS)
    assert start.isoformat() == DAYS[0]["lessons"][0]["start"]
    assert end.isoformat() == DAYS[0]["lessons"][1]["end"]
    item["heading"] = "שעורים 3 - 4"
    assert notice_time_range(item, DAYS) == (start, end)


def test_single_period_change_and_explicit_all_day():
    item = {"date": "2026-11-23", "heading": "שעור 3", "text": "ביטול שיעור"}
    start, end = notice_time_range(item, DAYS)
    assert start.hour == 10 and end.minute == 45
    item["text"] += "\nבמשך כל היום"
    assert notice_time_range(item, DAYS) is None


def test_missing_or_ambiguous_times_do_not_invent_event_times():
    item = {"date": "2026-11-23", "text": "שעורים 3 - 4"}
    missing = deepcopy(DAYS)
    missing[0]["lessons"][1]["start"] = None
    assert notice_time_range(item, missing) is None
    assert notice_time_range({**item, "date": "2026-11-24"}, DAYS) is None
    assert notice_time_range({**item, "text": "שעורים 3 - 5"}, DAYS) is None
    assert notice_time_range({**item, "text": "שעור 3\nAnother event\nשעור 4"}, DAYS) is None
    assert notice_time_range({**item, "text": "שעורים 3, 4"}, DAYS) is None

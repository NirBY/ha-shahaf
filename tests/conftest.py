"""Fictional fixtures only; never record live school/account payloads."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.shahaf.model import TZ, sunday

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def enable_integrations(enable_custom_integrations):
    yield


def week_payload(week):
    def text(value, style=""):
        return {"t": value, "s": {"s": style}}

    return {
        "views": [
            {
                "t": "מערכת",
                "tb": {
                    "l": {"date": (week + timedelta(days=7)).strftime("%Y%m%d")},
                    "r": {"date": (week - timedelta(days=7)).strftime("%Y%m%d")},
                },
                "d": [
                    {
                        "k": week.strftime("%m%d"),
                        "r": [
                            {
                                "h": [text("1"), text("08:30"), text("09:15")],
                                "i": [
                                    text("Math", ":7::::bold::::0:0"),
                                    text("Teacher A"),
                                    text("English", ":7::::bold::::0:0"),
                                    text("Teacher B"),
                                ],
                            },
                            {"h": [text("2"), text("09:15"), text("10:00")], "i": []},
                        ],
                    }
                ],
            },
            {
                "t": "שינויים",
                "d": [
                    {
                        "r": [
                            {"h": [text("יום א, 22 נובמבר")], "i": None},
                            {"h": [text("שעור 1")], "i": [text("מורה מחליפ/ה: Teacher C")]},
                            {"h": [text("מעודכן לתאריך 22/11/2026 שעה 06:45")], "i": None},
                        ]
                    }
                ],
            },
            {"t": "מבחנים", "d": [{"r": [{"h": [text("אין מבחנים")], "i": None}]}]},
            {
                "t": "אירועים",
                "d": [
                    {
                        "r": [
                            {
                                "h": [text("יום ה"), text("26"), text("נובמבר")],
                                "i": [text("מבחן במתמטיקה"), text("שעורים 1 - 2")],
                            },
                        ]
                    }
                ],
            },
        ],
        "props": [],
    }


@pytest.fixture
def payload():
    return week_payload(sunday(datetime.now(TZ).date()))


@pytest.fixture
def client():
    with (
        patch("custom_components.shahaf.config_flow.ShahafClient", autospec=True) as flow_cls,
        patch("custom_components.shahaf.ShahafClient", autospec=True) as setup_cls,
    ):
        instance = flow_cls.return_value
        setup_cls.return_value = instance
        instance.authenticate = AsyncMock(return_value={"Semel": 123456, "Grade": 7, "Class": 1})
        instance.schools = AsyncMock(
            return_value=[
                {"name": "Fictional Middle School", "semel": 123456, "code": 1},
                {"name": "Fictional High School", "semel": 123456, "code": 2},
            ]
        )
        instance.classes = AsyncMock(
            return_value=[{"Id": 6, "Name": "ז - 6", "Grade": 7, "Number": 6}]
        )
        instance.timetable = AsyncMock(
            side_effect=lambda campus, class_id, week: week_payload(week)
        )
        yield instance

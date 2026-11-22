from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shahaf.api import InvalidAuth, ShahafError
from custom_components.shahaf.const import DOMAIN
from custom_components.shahaf.diagnostics import async_get_config_entry_diagnostics

DATA = {
    "school_id": "123456",
    "username": "fictional",
    "password": "secret",
    "campus_code": 1,
    "school_name": "Fictional school",
    "class_id": 6,
    "class_name": "ז - 6",
}


async def test_full_first_install_and_reload(hass, client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {key: DATA[key] for key in ("school_id", "username", "password")}
    )
    assert result["step_id"] == "campus"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"campus_code": "1"})
    assert result["step_id"] == "class"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "class_id": "6",
            "name": "Demo child",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.unique_id == "123456:1:6"
    assert entry.state.value == "loaded"
    states = [s for s in hass.states.async_all() if "shahaf" in s.entity_id]
    assert len(states) == 12
    assert all(s.state != "unavailable" for s in states)
    old_ids = {s.entity_id for s in states}
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert old_ids == {s.entity_id for s in hass.states.async_all() if "shahaf" in s.entity_id}
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "secret" not in str(diag) and "Teacher" not in str(diag)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_duplicate_class(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="123456:1:6")
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={key: DATA[key] for key in ("school_id", "username", "password")},
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"campus_code": "1"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"class_id": "6"})
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("error", "reason"), [(InvalidAuth(), "invalid_auth"), (ShahafError(), "cannot_connect")]
)
async def test_login_error(hass, client, error, reason):
    client.authenticate.side_effect = error
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={key: DATA[key] for key in ("school_id", "username", "password")},
    )
    assert result["errors"] == {"base": reason}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_failed_refresh_keeps_last_data_but_marks_unavailable(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="123456:1:6")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    previous = coordinator.data
    client.timetable.side_effect = ShahafError("offline")
    await coordinator.async_refresh()
    assert coordinator.data is previous
    assert coordinator.last_update_success is False
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_calendar_limits_and_exclusive_end(hass, client):
    from custom_components.shahaf.calendar import ShahafCalendar

    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="123456:1:6")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    calendar = ShahafCalendar(entry.runtime_data, "lessons")
    events = calendar._events()
    assert len(events) == 2
    assert await calendar.async_get_events(hass, events[0].end, events[1].start) == []
    future = datetime.now(UTC) + timedelta(days=40)
    assert await calendar.async_get_events(hass, future, future + timedelta(days=1)) == []
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reauth_updates_existing_entry(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="123456:1:6")
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=DATA
    )
    assert result["step_id"] == "reauth_confirm"
    with patch("homeassistant.config_entries.ConfigEntries.async_reload", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "fictional",
                "password": "new_secret",
            },
        )
    assert result["reason"] == "reauth_successful"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data["password"] == "new_secret"


async def test_all_data_calendar_preserves_notices_and_untimed_lessons(hass, client):
    from custom_components.shahaf.calendar import ShahafCalendar

    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="123456:1:6")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    data = entry.runtime_data.data
    day = data["days"][0]
    day["lessons"][0]["start"] = day["lessons"][0]["end"] = None
    data["notices"] = [{"date": None, "heading": "", "text": "Bring a notebook"}]
    data["changes"] = [{"date": day["date"], "heading": "Period 3", "text": "ביטול שיעור"}]
    events = ShahafCalendar(entry.runtime_data, "all_data")._events()
    assert any(e.summary.startswith("1:") and not isinstance(e.start, datetime) for e in events)
    cancelled = next(e for e in events if "ביטול שיעור" in e.summary)
    assert "Period 3" in cancelled.description
    assert all("Bring a notebook" in e.description for e in events)
    assert not any(e.summary == "Bring a notebook" for e in events)
    assert await hass.config_entries.async_unload(entry.entry_id)

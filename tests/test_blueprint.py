from datetime import timedelta
from pathlib import Path

from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util import yaml


async def test_cancellation_blueprint_routes_only_new_explicit_notices(hass):
    raw = yaml.load_yaml(str(Path("blueprints/automation/shahaf/cancellation_greenapi.yaml")))
    config = yaml.substitute(
        raw,
        {
            "changes_sensor": "sensor.shahaf_demo_changes",
            "class_label": "Demo child",
            "recipient": "+12345678900",
            "notify_action": "notify.greenapi",
        },
    )
    config.pop("blueprint")
    calls = []

    async def record(call):
        calls.append(call.data)

    hass.services.async_register("notify", "greenapi", record)
    hass.states.async_set("sensor.shahaf_demo_changes", "0", {"items": []})
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_block_till_done()
    tomorrow = (dt_util.now().date() + timedelta(days=1)).isoformat()
    cancellation = {"date": tomorrow, "heading": "שעור 1", "text": "Math\nביטול שיעור"}
    replacement = {"date": tomorrow, "heading": "שעור 2", "text": "ממלא מקום"}
    hass.states.async_set("sensor.shahaf_demo_changes", "2", {"items": [cancellation, replacement]})
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0]["target"] == ["12345678900@c.us"]
    assert "Demo child" in calls[0]["message"] and "שעור 1" in calls[0]["message"]
    hass.states.async_set(
        "sensor.shahaf_demo_changes",
        "2",
        {
            "items": [cancellation, replacement],
            "fetched_at": "later",
        },
    )
    await hass.async_block_till_done()
    assert len(calls) == 1
    hass.states.async_set(
        "sensor.shahaf_demo_changes",
        "unavailable",
        {
            "items": [cancellation, replacement],
            "data_stale": True,
        },
    )
    await hass.async_block_till_done()
    assert len(calls) == 1

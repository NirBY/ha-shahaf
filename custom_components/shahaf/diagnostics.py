"""Diagnostics deliberately exclude credentials, names, IDs and lesson text."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "version": entry.version,
        "last_update_success": coordinator.last_update_success,
        "refresh_minutes": coordinator.update_interval.total_seconds() / 60,
        "fetched_at": data.get("fetched_at"),
        "source_updated_at": data.get("source_updated_at"),
        "published_days": len(data.get("days", [])),
        "lesson_slots": sum(len(d["lessons"]) for d in data.get("days", [])),
        "changes": len(data.get("changes", [])),
    }

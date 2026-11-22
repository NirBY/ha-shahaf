"""Shahaf Timetable integration."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .api import ShahafClient
from .const import CONF_SCHOOL_ID
from .coordinator import ShahafCoordinator

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR, Platform.BUTTON]
type ShahafConfigEntry = ConfigEntry[ShahafCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ShahafConfigEntry) -> bool:
    client = ShahafClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_SCHOOL_ID],
    )
    coordinator = ShahafCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def update_clock(_now):
        # Advance next-lesson and midnight-derived values without more HTTP requests.
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_interval(hass, update_clock, timedelta(minutes=1)))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ShahafConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ShahafConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

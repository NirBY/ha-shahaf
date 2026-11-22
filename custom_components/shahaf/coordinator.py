"""Fetch two explicit weeks atomically and distinguish failures from empty days."""

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InvalidAuth, ShahafClient, ShahafError
from .const import (
    CONF_CAMPUS_CODE,
    CONF_CLASS_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .model import TZ, combine_weeks, parse_week, sunday

_LOGGER = logging.getLogger(__name__)


class ShahafCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ShahafClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict:
        today = datetime.now(TZ).date()
        week = sunday(today)
        try:
            first = parse_week(
                await self.client.timetable(
                    self.entry.data[CONF_CAMPUS_CODE], self.entry.data[CONF_CLASS_ID], week
                ),
                week,
            )
            next_week = week + timedelta(days=7)
            second = parse_week(
                await self.client.timetable(
                    self.entry.data[CONF_CAMPUS_CODE], self.entry.data[CONF_CLASS_ID], next_week
                ),
                next_week,
            )
        except InvalidAuth:
            raise ConfigEntryAuthFailed("Shahaf login expired or was rejected") from None
        except (ShahafError, KeyError, TypeError, ValueError):
            raise UpdateFailed("Unable to read the published Shahaf timetable") from None
        return {**combine_weeks(first, second), "fetched_at": datetime.now(TZ).isoformat()}

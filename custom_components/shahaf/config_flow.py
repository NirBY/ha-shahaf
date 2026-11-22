"""UI setup, polling options and credential recovery."""

from datetime import datetime

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import InvalidAuth, NoData, ShahafClient, ShahafError
from .const import (
    CONF_CAMPUS_CODE,
    CONF_CLASS_ID,
    CONF_CLASS_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .model import TZ, parse_week, sunday

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _select(choices):
    return SelectSelector(
        SelectSelectorConfig(
            options=[{"value": str(key), "label": name} for key, name in choices],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class ShahafConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}
        self._client = None
        self._schools = []
        self._classes = []

    def _make_client(self, data):
        return ShahafClient(
            async_get_clientsession(self.hass),
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            data[CONF_SCHOOL_ID],
        )

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_SCHOOL_ID: str(user_input[CONF_SCHOOL_ID]).strip(),
            }
            self._client = self._make_client(data)
            try:
                await self._client.authenticate()
                self._schools = await self._client.schools()
                if not self._schools:
                    errors["base"] = "school_not_found"
                else:
                    self._data = data
                    return await self.async_step_campus()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ShahafError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHOOL_ID): vol.All(str, vol.Match(r"^\d{6}$")),
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): PASSWORD,
                }
            ),
        )

    async def async_step_campus(self, user_input=None):
        errors = {}
        if user_input is not None:
            school = next(
                (s for s in self._schools if str(s["code"]) == str(user_input[CONF_CAMPUS_CODE])),
                None,
            )
            if school is None:
                errors["base"] = "school_not_found"
            else:
                try:
                    self._classes = await self._client.classes(int(school["code"]))
                    if not self._classes:
                        errors["base"] = "no_data"
                    else:
                        self._data.update(
                            {
                                CONF_CAMPUS_CODE: int(school["code"]),
                                CONF_SCHOOL_NAME: school["name"],
                            }
                        )
                        return await self.async_step_class()
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except NoData:
                    errors["base"] = "no_data"
                except ShahafError:
                    errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="campus",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CAMPUS_CODE): _select(
                        (s["code"], s["name"]) for s in self._schools
                    )
                }
            ),
        )

    async def async_step_class(self, user_input=None):
        errors = {}
        if user_input is not None:
            school_class = next(
                (c for c in self._classes if str(c["Id"]) == str(user_input[CONF_CLASS_ID])), None
            )
            if school_class is None:
                errors["base"] = "no_data"
            else:
                await self.async_set_unique_id(
                    f"{self._data[CONF_SCHOOL_ID]}:{self._data[CONF_CAMPUS_CODE]}:{school_class['Id']}"
                )
                self._abort_if_unique_id_configured()
                try:
                    week = sunday(datetime.now(TZ).date())
                    parse_week(
                        await self._client.timetable(
                            self._data[CONF_CAMPUS_CODE], int(school_class["Id"]), week
                        ),
                        week,
                    )
                    self._data.update(
                        {
                            CONF_CLASS_ID: int(school_class["Id"]),
                            CONF_CLASS_NAME: school_class["Name"],
                        }
                    )
                    title = user_input.get(CONF_NAME, "").strip() or school_class["Name"]
                    return self.async_create_entry(title=title, data=self._data)
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except NoData:
                    errors["base"] = "no_data"
                except (ShahafError, ValueError, TypeError, KeyError):
                    errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="class",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLASS_ID): _select(
                        (c["Id"], c["Name"]) for c in self._classes
                    ),
                    vol.Optional(CONF_NAME): str,
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            client = self._make_client(data)
            try:
                await client.authenticate()
                schools = await client.schools()
                if not any(int(s["code"]) == entry.data[CONF_CAMPUS_CODE] for s in schools):
                    errors["base"] = "school_not_found"
                else:
                    week = sunday(datetime.now(TZ).date())
                    parse_week(
                        await client.timetable(data[CONF_CAMPUS_CODE], data[CONF_CLASS_ID], week),
                        week,
                    )
                    return self.async_update_reload_and_abort(entry, data_updates=user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except (ShahafError, ValueError, TypeError, KeyError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): PASSWORD,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ShahafOptionsFlow()


class ShahafOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                }
            ),
        )

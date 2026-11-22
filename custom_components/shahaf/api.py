"""Small asynchronous client for the endpoints used by Shahaf's Android app.

The API is unofficial. Never log request URLs: Shahaf requires credentials and
session tokens in query parameters. Only this fixed HTTPS origin is used.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import aiohttp

from .const import API_BASE


class ShahafError(Exception):
    """The service could not provide a valid response."""


class InvalidAuth(ShahafError):
    """The service rejected the account or session."""


class NoData(ShahafError):
    """The school has not published the requested data."""


class ShahafClient:
    """Share Home Assistant's HTTP session and keep the token only in memory."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str, school_id: str
    ) -> None:
        self.session = session
        self.username = username
        self.password = password
        self.school_id = school_id
        self._token: str | None = None
        self._auth_lock = asyncio.Lock()

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Return JSON without leaking query strings through exceptions."""
        try:
            async with self.session.get(
                API_BASE + path,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise InvalidAuth("Authentication rejected")
                if response.status != 200:
                    raise ShahafError(f"Shahaf returned HTTP {response.status}")
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError):
            raise ShahafError("Unable to read Shahaf's response") from None
        if isinstance(data, dict) and data.get("Status") == "failed":
            code = data.get("Error")
            if code in {"INVALID_TOKEN", "NO_TOKEN", "NO_USER_OR_PASSWORD", "INVALID_USER"}:
                raise InvalidAuth("Authentication rejected")
            if code == "NO_DATA":
                raise NoData("The school has not published this data")
            raise ShahafError("Shahaf rejected the request")
        return data

    async def authenticate(self) -> dict[str, Any]:
        """Validate the account; do not retain names or national identity numbers."""
        async with self._auth_lock:
            data = await self._request(
                "user/authstudent/",
                {"usr": self.username, "pwd": self.password},
            )
            if not isinstance(data, dict) or not isinstance(data.get("Token"), str):
                raise InvalidAuth("Login did not return a session")
            if not data["Token"]:
                raise InvalidAuth("Login did not return a session")
            self._token = data["Token"]
            return data.get("Student") or {}

    async def _authenticated(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._token is None:
            await self.authenticate()
        try:
            return await self._request(path, {**(params or {}), "token": self._token})
        except InvalidAuth:
            await self.authenticate()
            return await self._request(path, {**(params or {}), "token": self._token})

    async def schools(self) -> list[dict[str, Any]]:
        """List the campuses associated with the supplied ministry school ID."""
        data = await self._authenticated("school/student/")
        if not isinstance(data, list):
            raise ShahafError("Invalid school list")
        return [
            item
            for item in data
            if isinstance(item, dict) and str(item.get("semel")) == self.school_id
        ]

    async def classes(self, campus_code: int) -> list[dict[str, Any]]:
        """Class Id is an internal ID, not Grade * 100 + Number."""
        data = await self._authenticated(f"student/{self.school_id}/{int(campus_code)}/classes/")
        if not isinstance(data, dict) or not isinstance(data.get("Classes"), list):
            raise ShahafError("Invalid class list")
        return data["Classes"]

    async def timetable(self, campus_code: int, class_id: int, week: date) -> dict[str, Any]:
        """Read the app's dated views without registering a push-notification device."""
        data = await self._authenticated(
            f"view/{self.school_id}/{int(campus_code)}/appdata/",
            {"clsid": int(class_id), "date": week.strftime("%Y%m%d")},
        )
        if not isinstance(data, dict) or not isinstance(data.get("views"), list):
            raise ShahafError("Invalid timetable response")
        return data

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.shahaf.api import InvalidAuth, NoData, ShahafClient, ShahafError


def response(data, status=200):
    resp = MagicMock(status=status)
    resp.json = AsyncMock(return_value=data)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


async def test_exact_routes_and_token_refresh():
    session = MagicMock()
    session.get.side_effect = [
        response({"Token": "first", "Student": {}}),
        response({"Error": "INVALID_TOKEN", "Status": "failed"}),
        response({"Token": "second", "Student": {}}),
        response({"views": []}),
    ]
    client = ShahafClient(session, "fictional", "secret", "123456")
    await client.timetable(1, 6, date(2026, 11, 22))
    calls = session.get.call_args_list
    assert calls[0].args[0].endswith("user/authstudent/")
    assert calls[0].kwargs["params"] == {"usr": "fictional", "pwd": "secret"}
    assert calls[1].args[0].endswith("view/123456/1/appdata/")
    assert calls[3].kwargs["params"] == {"clsid": 6, "date": "20261122", "token": "second"}
    assert all(call.kwargs["allow_redirects"] is False for call in calls)


async def test_transport_error_does_not_expose_credentials():
    session = MagicMock()
    session.get.side_effect = aiohttp.ClientError("https://host/?pwd=secret&token=private")
    with pytest.raises(ShahafError) as error:
        await ShahafClient(session, "user", "secret", "123456").authenticate()
    assert "secret" not in str(error.value) and "private" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"Status": "failed", "Error": "INVALID_TOKEN"}, InvalidAuth),
        ({"Status": "failed", "Error": "NO_DATA"}, NoData),
    ],
)
async def test_failures_are_not_empty_data(data, error):
    session = MagicMock()
    session.get.return_value = response(data)
    with pytest.raises(error):
        await ShahafClient(session, "user", "secret", "123456")._request("school/student/")

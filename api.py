from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import DEVICE_LIST_ENDPOINT, LOGIN_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class MinjetApiError(Exception):
    """Base API error."""


class MinjetAuthError(MinjetApiError):
    """Authentication error."""


class MinjetApi:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None

    async def async_login(self) -> str:
        payload = {
            "username": self._username,
            "password": self._password,
        }

        _LOGGER.warning("Minjet login request starting for user: %s", self._username)

        async with self._session.post(
            LOGIN_ENDPOINT,
            json=payload,
            timeout=20,
        ) as resp:
            text = await resp.text()

        _LOGGER.warning("Minjet login response status=%s body=%s", resp.status, text)

        try:
            data = json.loads(text)
        except Exception as err:
            raise MinjetApiError(f"Login returned non-JSON: {text}") from err

        token = data.get("token")
        if resp.status != 200 or data.get("code") != 200 or not isinstance(token, str) or not token.strip():
            raise MinjetAuthError(f"Login failed: {data}")

        self._token = token.strip()
        _LOGGER.warning("Minjet token acquired, length=%s", len(self._token))
        return self._token

    async def async_get_devices(self) -> list[dict[str, Any]]:
        if not self._token:
            await self.async_login()

        if not isinstance(self._token, str) or not self._token.strip():
            raise MinjetAuthError(f"Token invalid after login: {self._token!r}")

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        _LOGGER.warning("Minjet device query starting with GET")

        async with self._session.get(
            DEVICE_LIST_ENDPOINT,
            headers=headers,
            timeout=20,
        ) as resp:
            text = await resp.text()

        _LOGGER.warning("Minjet device query response status=%s body=%s", resp.status, text)

        try:
            data = json.loads(text)
        except Exception as err:
            raise MinjetApiError(f"Device query returned non-JSON: {text}") from err

        if resp.status == 401:
            _LOGGER.error(
                "Minjet device query returned 401 Unauthorized. Token is likely expired; forcing re-login."
            )
            self._token = None
            raise MinjetAuthError("Unauthorized")

        if resp.status == 403:
            _LOGGER.error(
                "Minjet device query returned 403 Forbidden. Token may be expired/invalid; forcing re-login."
            )
            self._token = None
            raise MinjetAuthError("Forbidden")

        if 400 <= resp.status < 500:
            _LOGGER.error(
                "Minjet device query returned client error %s. Response body: %s",
                resp.status,
                text,
            )
            raise MinjetApiError(f"Device query client error {resp.status}: {data}")

        if resp.status != 200 or data.get("code") != 200:
            raise MinjetApiError(f"Device query failed: {data}")

        devices = data.get("data", [])
        if not isinstance(devices, list):
            raise MinjetApiError(f"Unexpected response: {data}")

        return devices

    async def async_test_credentials(self) -> None:
        await self.async_login()
        await self.async_get_devices()

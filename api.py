from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

from .const import DEVICE_LIST_ENDPOINT, LOGIN_ENDPOINT, TOKEN_REFRESH_INTERVAL_SECONDS

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
        self._token_acquired_at: float | None = None
        self._token_generation = 0
        self._auth_lock = asyncio.Lock()

    async def async_login(self) -> str:
        payload = {
            "username": self._username,
            "password": self._password,
        }

        _LOGGER.debug("Minjet login request starting for user: %s", self._username)

        async with self._session.post(
            LOGIN_ENDPOINT,
            json=payload,
            timeout=20,
        ) as resp:
            text = await resp.text()

        _LOGGER.debug("Minjet login response status=%s body=%s", resp.status, text)

        try:
            data = json.loads(text)
        except Exception as err:
            raise MinjetApiError(f"Login returned non-JSON: {text}") from err

        token = data.get("token")
        if resp.status != 200 or data.get("code") != 200 or not isinstance(token, str) or not token.strip():
            raise MinjetAuthError(f"Login failed: {data}")

        self._token = token.strip()
        self._token_acquired_at = time.time()
        self._token_generation += 1
        _LOGGER.debug("Minjet token acquired, length=%s", len(self._token))
        return self._token

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def token_generation(self) -> int:
        return self._token_generation

    def token_needs_refresh(self) -> bool:
        return self._token_needs_refresh()

    def _token_needs_refresh(self) -> bool:
        if not self._token:
            return True
        if not self._token_acquired_at:
            return True
        age_seconds = time.time() - self._token_acquired_at
        return age_seconds >= TOKEN_REFRESH_INTERVAL_SECONDS

    async def _ensure_valid_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and not self._token_needs_refresh():
            token = self._token
            if isinstance(token, str) and token.strip():
                return token

        async with self._auth_lock:
            if not force_refresh and not self._token_needs_refresh():
                token = self._token
                if isinstance(token, str) and token.strip():
                    return token
            return await self.async_login()

    async def async_refresh_token(self, force_refresh: bool = False) -> str:
        return await self._ensure_valid_token(force_refresh=force_refresh)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        for attempt in (1, 2):
            force_refresh = attempt == 2
            await self._ensure_valid_token(force_refresh=force_refresh)

            if not isinstance(self._token, str) or not self._token.strip():
                raise MinjetAuthError(f"Token invalid after login: {self._token!r}")

            headers = {
                "Authorization": f"Bearer {self._token}",
            }

            _LOGGER.debug("Minjet device query starting with GET")

            async with self._session.get(
                DEVICE_LIST_ENDPOINT,
                headers=headers,
                timeout=20,
            ) as resp:
                text = await resp.text()

            _LOGGER.debug("Minjet device query response status=%s body=%s", resp.status, text)

            try:
                data = json.loads(text)
            except Exception as err:
                raise MinjetApiError(f"Device query returned non-JSON: {text}") from err

            if resp.status in (401, 403):
                _LOGGER.warning(
                    "Minjet device query returned %s. Refreshing token and retrying once.",
                    resp.status,
                )
                self._token = None
                self._token_acquired_at = None
                if attempt == 1:
                    continue
                raise MinjetAuthError(f"Unauthorized ({resp.status})")

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

        raise MinjetAuthError("Unable to refresh token")

    async def async_test_credentials(self) -> None:
        await self.async_login()
        await self.async_get_devices()

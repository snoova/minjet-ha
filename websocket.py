from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random

import aiohttp
from .const import WSS_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class MinjetWebSocketClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        on_message,
        on_connected=None,
        on_disconnected=None,
    ):
        self._session = session
        self._token = token

        self._on_message = on_message
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected

        self._ws = None
        self._task = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run())

    def set_token(self, token: str) -> None:
        self._token = token

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        self._ws = None

    async def _run(self):
        retry = 0

        while self._running:
            connected = False
            try:
                url = WSS_ENDPOINT.format(token=self._token)
                _LOGGER.debug("Minjet WSS connecting...")

                async with self._session.ws_connect(url) as ws:
                    self._ws = ws
                    _LOGGER.debug("Minjet WSS connected")
                    connected = True

                    retry = 0

                    if self._on_connected:
                        await self._on_connected()

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break

            except Exception as e:
                _LOGGER.warning("WSS connection failed: %s", e)
            finally:
                self._ws = None

            if connected and self._on_disconnected:
                await self._on_disconnected()
            if not self._running:
                break

            retry += 1
            delay = min(60, (2 ** retry)) + random.uniform(0, 2)
            await asyncio.sleep(delay)

    async def _handle_message(self, data: str):
        try:
            payload = json.loads(data)
            if payload.get("type") == "detail":
                await self._on_message(payload)
        except Exception as e:
            _LOGGER.error("WSS parse error: %s", e)

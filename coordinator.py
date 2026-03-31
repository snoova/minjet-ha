from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MinjetApi
from .const import DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL
from .websocket import MinjetWebSocketClient

_LOGGER = logging.getLogger(__name__)


class MinjetCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass,
        api: MinjetApi,
        enable_websocket: bool = False,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ):
        try:
            scan_interval = int(scan_interval)
        except (TypeError, ValueError):
            scan_interval = DEFAULT_SCAN_INTERVAL
        scan_interval = max(MIN_SCAN_INTERVAL, scan_interval)
        super().__init__(
            hass,
            _LOGGER,
            name="Minjet",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._enable_websocket = enable_websocket

        self._rest_data: dict = {}
        self._wss_data: dict = {}
        self._wss_connected = False
        self._last_update_source = "rest"

        self._ws_client: MinjetWebSocketClient | None = None

    async def async_setup(self):
        if not self._rest_data:
            devices = await self.api.async_get_devices()
            self._rest_data = devices[0] if devices else {}

        if self._enable_websocket:
            await self._start_websocket()

    async def _start_websocket(self):
        try:
            if self._ws_client:
                return

            token = self.api.token
            if not token:
                _LOGGER.debug("No token for WSS")
                return

            session = self.api.session

            self._ws_client = MinjetWebSocketClient(
                session=session,
                token=token,
                on_message=self._handle_wss_message,
                on_connected=self._handle_wss_connected,
                on_disconnected=self._handle_wss_disconnected,
            )

            await self._ws_client.start()

        except Exception as e:
            _LOGGER.error("Failed to start WSS: %s", e)

    async def _stop_websocket(self):
        if self._ws_client:
            await self._ws_client.stop()
            self._ws_client = None
        self._wss_connected = False
        self._last_update_source = "rest"

    async def _restart_websocket(self):
        await self._stop_websocket()
        await self._start_websocket()

    async def _handle_wss_connected(self):
        self._wss_connected = True
        self._last_update_source = "websocket"
        self.async_set_updated_data(self._merge_data(False))

    async def _handle_wss_disconnected(self):
        self._wss_connected = False
        self._last_update_source = "rest"
        self.async_set_updated_data(self._merge_data(False))

    async def _handle_wss_message(self, payload: dict):
        data = payload.get("data")
        if not data:
            return

        self._wss_data = data
        self._wss_connected = True
        self._last_update_source = "websocket"

        self.async_set_updated_data(self._merge_data(False))

    async def _async_update_data(self):
        try:
            ws_restarted_for_token = False
            if self._enable_websocket and self._ws_client and self.api.token_needs_refresh():
                _LOGGER.debug("Token exceeded refresh interval; reconnecting WebSocket with fresh token")
                await self._stop_websocket()
                await self.api.async_refresh_token(force_refresh=True)
                await self._start_websocket()
                ws_restarted_for_token = True

            token_generation_before = self.api.token_generation
            devices = await self.api.async_get_devices()
            device = devices[0] if devices else {}
            device_offline = not bool(device) or device.get("properties") is None
            token_was_refreshed = self.api.token_generation != token_generation_before

            if device_offline:
                _LOGGER.debug("Device offline detected")
            else:
                self._rest_data = device
                if not self._wss_connected:
                    self._last_update_source = "rest"

            if not self._rest_data:
                _LOGGER.debug("First load: accepting offline device as base data")
                self._rest_data = device

            if self._enable_websocket:
                if token_was_refreshed and self._ws_client and not ws_restarted_for_token:
                    _LOGGER.debug("Token refreshed during REST update; reconnecting WebSocket")
                    await self._restart_websocket()
                elif not self._ws_client:
                    await self._start_websocket()
                elif self.api.token:
                    self._ws_client.set_token(self.api.token)

            return self._merge_data(device_offline)

        except Exception as e:
            _LOGGER.error("REST update failed: %s", e)
            raise UpdateFailed(f"REST update failed: {e}") from e

    def _merge_data(self, device_offline: bool):
        base = dict(self._rest_data)

        if self._wss_data:
            base["properties"] = {
                **(self._rest_data.get("properties") or {}),
                **(self._wss_data.get("properties") or {}),
            }

        now = time.time()

        prev_connection = (self.data or {}).get("_connection", {}) or {}

        if device_offline:
            offline_since = prev_connection.get("offline_since") or now
        else:
            offline_since = None

        base["_connection"] = {
            "websocket_enabled": self._enable_websocket,
            "websocket_connected": self._wss_connected,
            "last_update_source": self._last_update_source,
            "device_offline": device_offline,
            "offline_since": offline_since,
        }

        return base

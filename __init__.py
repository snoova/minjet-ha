from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MinjetApi
from .const import (
    CONF_ENABLE_WEBSOCKET,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_WEBSOCKET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import MinjetCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["logger"] = _LOGGER
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = MinjetApi(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    enable_websocket = entry.options.get(
        CONF_ENABLE_WEBSOCKET,
        entry.data.get(CONF_ENABLE_WEBSOCKET, DEFAULT_ENABLE_WEBSOCKET),
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = MinjetCoordinator(
        hass,
        api,
        enable_websocket=enable_websocket,
        scan_interval=scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data:
            coordinator = data.get("coordinator")
            ws_client = getattr(coordinator, "_ws_client", None)
            if ws_client:
                await ws_client.stop()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

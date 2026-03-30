from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MinjetApi, MinjetAuthError
from .const import (
    CONF_ENABLE_WEBSOCKET,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_WEBSOCKET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class MinjetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate_input(self, user_input: dict) -> None:
        session = async_get_clientsession(self.hass)
        api = MinjetApi(
            session=session,
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
        await api.async_test_credentials()

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                await self._validate_input(user_input)
            except MinjetAuthError:
                _LOGGER.exception("Minjet auth failed")
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                _LOGGER.exception("Minjet connection failed")
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected Minjet error: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_ENABLE_WEBSOCKET: user_input.get(
                            CONF_ENABLE_WEBSOCKET,
                            DEFAULT_ENABLE_WEBSOCKET,
                        ),
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL,
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(
                    CONF_ENABLE_WEBSOCKET,
                    default=DEFAULT_ENABLE_WEBSOCKET,
                ): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        errors = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                await self._validate_input(user_input)
            except MinjetAuthError:
                _LOGGER.exception("Minjet auth failed during reconfigure")
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                _LOGGER.exception("Minjet connection failed during reconfigure")
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected Minjet reconfigure error: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        **entry.options,
                        CONF_ENABLE_WEBSOCKET: user_input.get(
                            CONF_ENABLE_WEBSOCKET,
                            entry.options.get(
                                CONF_ENABLE_WEBSOCKET,
                                DEFAULT_ENABLE_WEBSOCKET,
                            ),
                        ),
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL,
                            entry.options.get(
                                CONF_SCAN_INTERVAL,
                                DEFAULT_SCAN_INTERVAL,
                            ),
                        ),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data.get(CONF_USERNAME, ""),
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=entry.data.get(CONF_PASSWORD, ""),
                ): str,
                vol.Optional(
                    CONF_ENABLE_WEBSOCKET,
                    default=entry.options.get(
                        CONF_ENABLE_WEBSOCKET,
                        DEFAULT_ENABLE_WEBSOCKET,
                    ),
                ): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.options.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return MinjetOptionsFlow(config_entry)


class MinjetOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_WEBSOCKET,
                    default=self._config_entry.options.get(
                        CONF_ENABLE_WEBSOCKET,
                        DEFAULT_ENABLE_WEBSOCKET,
                    ),
                ): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

"""Configuration par l'interface : l'adresse de ZIONIA et la clé d'API."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import CleRefusee, verifier
from .const import CONF_LECTEUR, CONF_URL, CONF_VOIX, DEFAULT_URL, DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


class ZioniaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Demande l'adresse et la clé, et les vérifie avant d'enregistrer."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ZioniaOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        erreurs: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            cle = user_input[CONF_API_KEY].strip()

            try:
                compte = await verifier(self.hass, url, cle)
            except CleRefusee:
                erreurs["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                erreurs["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{url}|{compte}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ZIONIA ({compte})" if compte else "ZIONIA",
                    data={CONF_URL: url, CONF_API_KEY: cle},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
            errors=erreurs,
        )


class ZioniaOptionsFlow(OptionsFlow):
    """Choisit l'enceinte qui lit les réponses.

    Assist lit une réponse sur l'appareil qui a écouté : l'ordinateur,
    le téléphone. Pour l'entendre sur le Google Home, on passait par
    une automatisation qui reconnaissait « Demande à ZIONIA … » — mais
    Whisper transcrit ce nom en « Azionia », « Zion Yacht » ou
    « Dis-moi », et chaque variante était à ajouter à la main. Choisi
    ici, le lecteur reçoit toutes les réponses, quelle que soit la
    phrase.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_LECTEUR): EntitySelector(
                    EntitySelectorConfig(domain="media_player")
                ),
                vol.Optional(CONF_VOIX): EntitySelector(
                    EntitySelectorConfig(domain="tts")
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
        )

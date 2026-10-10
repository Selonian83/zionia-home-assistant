"""L'agent de conversation : la phrase reconnue part à ZIONIA."""

from __future__ import annotations

import logging
from typing import Literal

import aiohttp

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import CleRefusee, ReponseIllisible, demander
from .const import CONF_LECTEUR, CONF_URL, CONF_VOIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crée l'agent."""
    async_add_entities([ZioniaAgent(entry)])


class ZioniaAgent(conversation.ConversationEntity):
    """Transmet chaque phrase à ZIONIA et rend sa réponse.

    Aucune commande de la maison ici : ZIONIA ne pilote pas les
    lumières. Pour que « allume le salon » marche quand même, cocher
    « Préférer le traitement local des commandes » dans l'assistant
    vocal : Home Assistant traite alors ce qu'il connaît, et ne passe
    à ZIONIA que le reste.
    """

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ZIONIA",
            manufacturer="TeamDevQC",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """ZIONIA répond dans la langue de la question."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Pose la question à ZIONIA et inscrit sa réponse.

        Les pannes deviennent des phrases : l'utilisateur parle à une
        enceinte, il n'a pas d'écran pour lire un message d'erreur.
        """
        try:
            reponse = await demander(
                self.hass,
                self.entry.data[CONF_URL],
                self.entry.data[CONF_API_KEY],
                user_input.text,
            )
        except CleRefusee:
            reponse = "ZIONIA refuse la clé d'API. Il faut en créer une nouvelle."
        except TimeoutError:
            reponse = "ZIONIA met trop de temps à répondre. Réessaie dans un moment."
        except ReponseIllisible as erreur:
            _LOGGER.warning("ZIONIA : réponse illisible (%s)", erreur)
            reponse = (
                "ZIONIA a mis trop de temps à répondre et la connexion a été coupée."
                if erreur.statut in (502, 503, 504)
                else "ZIONIA a renvoyé une réponse que je ne comprends pas."
            )
        except aiohttp.ClientError:
            reponse = "Je n'arrive pas à joindre ZIONIA."
        except Exception:  # noqa: BLE001
            # Dernier filet : une exception qui remonterait ici
            # s'afficherait « [object Object] » dans Assist, sans rien
            # dire de la cause. On la journalise, et on le dit.
            _LOGGER.exception("ZIONIA : erreur inattendue")
            reponse = "Une erreur inattendue est survenue. Elle est dans le journal de Home Assistant."

        reponse = reponse or "ZIONIA n'a rien répondu."

        # Lue sur l'enceinte choisie : l'appareil qui a écouté se tait,
        # sans quoi on l'entendrait deux fois. Un texte vide fait
        # sauter la synthèse vocale à Assist.
        if self._lire_ailleurs(reponse):
            reponse = ""

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=user_input.agent_id,
                content=reponse,
            )
        )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    def _lire_ailleurs(self, reponse: str) -> bool:
        """Fait lire la réponse sur l'enceinte des options, s'il y en a une.

        Sans voix choisie, la première synthèse vocale installée —
        Piper, en pratique.
        """
        lecteur = self.entry.options.get(CONF_LECTEUR)
        if not lecteur:
            return False

        voix = self.entry.options.get(CONF_VOIX) or next(
            iter(self.hass.states.async_entity_ids("tts")), None
        )
        if not voix:
            _LOGGER.warning("ZIONIA : aucune synthèse vocale pour lire sur %s", lecteur)
            return False

        self.hass.async_create_task(
            self.hass.services.async_call(
                "tts",
                "speak",
                {"media_player_entity_id": lecteur, "message": reponse},
                target={"entity_id": voix},
            )
        )
        return True

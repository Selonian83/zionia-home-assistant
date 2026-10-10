"""Les deux appels à ZIONIA : vérifier la clé, poser une question."""

from __future__ import annotations

import json

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DELAI_REPONSE, DELAI_VERIFICATION


class CleRefusee(Exception):
    """ZIONIA ne reconnaît pas la clé d'API."""


class ReponseIllisible(Exception):
    """La réponse n'est pas du JSON de ZIONIA.

    Le cas typique : le relais devant zionia.app a coupé l'attente et
    renvoyé sa propre page d'erreur HTML, une 502 ou une 504.
    """

    def __init__(self, statut: int) -> None:
        super().__init__(f"HTTP {statut}")
        self.statut = statut


def _entetes(cle: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {cle}"}


async def verifier(hass: HomeAssistant, url: str, cle: str) -> str:
    """Renvoie le courriel du compte si la clé est valide."""
    session = async_get_clientsession(hass)
    async with session.get(
        f"{url}/api/voix",
        headers=_entetes(cle),
        timeout=aiohttp.ClientTimeout(total=DELAI_VERIFICATION),
    ) as reponse:
        if reponse.status == 401:
            raise CleRefusee
        reponse.raise_for_status()
        donnees = await reponse.json(content_type=None)
        return str(donnees.get("compte", ""))


async def demander(hass: HomeAssistant, url: str, cle: str, texte: str) -> str:
    """Pose la question et renvoie la réponse à lire à voix haute.

    Les refus du serveur (quota, erreur) portent eux aussi une phrase
    prête à dire dans « reponse » : on la préfère au message technique.
    """
    session = async_get_clientsession(hass)
    async with session.post(
        f"{url}/api/voix",
        json={"texte": texte},
        headers=_entetes(cle),
        timeout=aiohttp.ClientTimeout(total=DELAI_REPONSE),
    ) as reponse:
        if reponse.status == 401:
            raise CleRefusee

        # Lu en texte, puis décodé : un relais peut répondre en HTML, et
        # json() lèverait alors une erreur que personne n'attend.
        brut = await reponse.text()
        try:
            donnees = json.loads(brut)
        except ValueError as erreur:
            raise ReponseIllisible(reponse.status) from erreur

        if not isinstance(donnees, dict):
            raise ReponseIllisible(reponse.status)

        return str(donnees.get("reponse") or donnees.get("error") or "")

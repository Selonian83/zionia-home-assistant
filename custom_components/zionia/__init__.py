"""ZIONIA comme agent de conversation de Home Assistant.

La reconnaissance vocale (Whisper) et la synthèse (Piper) restent
dans Home Assistant. Cette intégration ne fait que le milieu : elle
envoie la phrase reconnue à ZIONIA et renvoie sa réponse à lire.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.CONVERSATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Crée l'agent de conversation."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Retire l'agent de conversation."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Constantes de l'intégration ZIONIA."""

DOMAIN = "zionia"

CONF_URL = "url"

# Options : où lire les réponses. Sans lecteur, Assist les lit sur
# l'appareil qui a écouté, comme n'importe quel agent.
CONF_LECTEUR = "lecteur"
CONF_VOIX = "voix"
DEFAULT_URL = "https://zionia.app"

# Sur processeur, une réponse qui cherche dans la documentation prend
# facilement une minute. Couper avant laisserait ZIONIA finir dans le
# vide pendant que Home Assistant annonce une erreur.
DELAI_REPONSE = 180

# La vérification de la clé ne fait tourner aucun modèle.
DELAI_VERIFICATION = 15

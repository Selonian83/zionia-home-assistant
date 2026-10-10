# ZIONIA pour Home Assistant

Parle à [ZIONIA](https://zionia.app), l'assistant de programmation, avec
l'assistant vocal de Home Assistant. Tu poses ta question à voix haute,
et ZIONIA répond sur l'enceinte de ton choix, par exemple un Google Home.

```
micro (téléphone, ordinateur, Voice PE)
  → Whisper : la voix devient du texte          (dans Home Assistant)
  → ZIONIA  : la question part à zionia.app     (cette intégration)
  → Piper   : la réponse devient une voix       (dans Home Assistant)
  → enceinte
```

Chaque échange est aussi enregistré dans ton compte ZIONIA, dans une
conversation par jour (« Voix — 10 octobre »). Tu y retrouves la réponse
complète, avec le code et les sources que la voix ne lit pas.

## Ce qu'il te faut

- Home Assistant **2026.2** ou plus récent
- [HACS](https://hacs.xyz/docs/use/)
- un compte sur [zionia.app](https://zionia.app)

## 1. Installer l'intégration

1. Dans Home Assistant, ouvre **HACS**.
2. ⋮ en haut à droite → **Dépôts personnalisés**.
3. Dépôt : `https://github.com/Selonian83/zionia-home-assistant`,
   type : **Intégration**, puis **Ajouter**.
4. Cherche **ZIONIA** dans HACS → **Télécharger**.
5. Redémarre Home Assistant : **Paramètres → Système**, bouton
   d'alimentation en haut à droite → **Redémarrer Home Assistant**.

Les mises à jour apparaîtront ensuite d'elles-mêmes dans HACS.

## 2. Créer une clé d'API

Sur [zionia.app](https://zionia.app) : **Paramètres → Clés d'API →
Créer une clé**.

La clé commence par `zk_` et n'est affichée **qu'une fois** : copie-la tout
de suite. Elle ne donne accès qu'aux questions vocales de ton compte, et
elle se révoque au même endroit, sans changer ton mot de passe.

## 3. Ajouter ZIONIA à Home Assistant

**Paramètres → Appareils et services → Ajouter une intégration → ZIONIA**

- Adresse : `https://zionia.app`
- Clé d'API : celle de l'étape 2

La clé est vérifiée tout de suite.

## 4. Configurer l'assistant vocal

Il faut d'abord la reconnaissance et la synthèse vocales. Le plus simple
est d'installer les modules complémentaires **Whisper** (langue `fr`) et
**Piper** (une voix `fr_FR`), puis d'ajouter leurs intégrations Wyoming
quand Home Assistant les propose dans **Découvertes**.

Ensuite : **Paramètres → Assistants vocaux → Ajouter un assistant**

- Langue : Français
- **Agent de conversation : ZIONIA**
- Reconnaissance vocale : Whisper
- Synthèse vocale : Piper
- Coche **« Préférer le traitement local des commandes »** : « allume le
  salon » reste traité par Home Assistant, plus vite, et seules les vraies
  questions partent à ZIONIA.

## 5. Choisir l'enceinte *(facultatif)*

Par défaut, la réponse est lue sur l'appareil qui a écouté : le téléphone
ou l'ordinateur. Pour l'entendre sur une enceinte, par exemple un Google
Home ajouté avec l'intégration Google Cast :

**Paramètres → Appareils et services → ZIONIA → Configurer** (l'engrenage)

- **Enceinte** : ton Google Home
- **Synthèse vocale** : laisse vide pour Piper

Toutes les réponses de ZIONIA y sont alors lues, peu importe comment la
question est posée.

> Le Google Home bipe sans parler ? Il va chercher le son chez Home
> Assistant, à son adresse locale. Vérifie **Paramètres → Système →
> Réseau → URL locale** : par exemple `http://192.168.1.10:8123`.

## Parler sans cliquer *(facultatif)*

Avec un PC Windows et un casque, **ZIONIA Écoute** attend un mot
d'activation et pose la question tout seul, sans ouvrir Assist. Voir
[`ecoute/`](ecoute/README.md).

## Essayer sans micro

Ouvre **Assist** (l'icône de bulle en haut de la Vue d'ensemble) et tape
ta question. C'est le même chemin, sans Whisper.

## Délais

Home Assistant attend la réponse jusqu'à **3 minutes**. Une question qui
demande à ZIONIA de chercher dans la documentation prend plus de temps
qu'une salutation.

## Quand ça ne marche pas

| Ce que tu entends | Ce qu'il faut faire |
|---|---|
| « ZIONIA refuse la clé d'API » | La clé a été révoquée : crée-en une autre, supprime l'intégration et ajoute-la de nouveau. |
| « Tu as atteint ta limite de questions » | La voix compte dans le même quota que le site. |
| « Je n'ai rien entendu » | Le micro n'a capté que du silence : rapproche-toi, ou vérifie le micro choisi par le navigateur. |
| « Je n'arrive pas à joindre ZIONIA » | Home Assistant n'a pas accès à internet, ou zionia.app est indisponible. |

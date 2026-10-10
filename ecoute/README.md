# ZIONIA Écoute — parler à ZIONIA sans cliquer

Un petit programme pour Windows. Il écoute le micro de ton casque en
permanence et attend le mot d'activation. Quand il l'entend :

```
« Hey Jarvis »        → bip aigu : il t'écoute
« c'est quoi Docker » → bip grave quand tu te tais
                      → Whisper transcrit, ZIONIA répond
                      → le Google Home dit la réponse
```

Le mot d'activation est reconnu **sur ton PC** : rien n'est envoyé
avant. Ensuite, c'est le même chemin que le bouton micro d'Assist.

## Ce qu'il faut avant

- L'intégration ZIONIA installée dans Home Assistant, avec l'**Enceinte**
  choisie dans ses options (sinon tu ne verras la réponse qu'à l'écran).
- Whisper installé dans Home Assistant.
- Le PC allumé, le casque branché.

## 1. Installer Python — une seule fois

Dans **PowerShell** :

```powershell
winget install -e --id Python.Python.3.12
```

**Ferme PowerShell et rouvre-le**, puis vérifie :

```powershell
py -3.12 --version
```

Ça doit afficher `Python 3.12.…`.

## 2. Récupérer le programme

```powershell
cd D:\
git clone https://github.com/Selonian83/zionia-home-assistant
cd D:\zionia-home-assistant\ecoute
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

L'installation prend une ou deux minutes.

## 3. Créer le jeton Home Assistant

1. Dans Home Assistant, clique sur **ton nom**, en bas à gauche.
2. Onglet **Sécurité**, tout en bas : **Jetons d'accès longue durée** →
   **Créer un jeton**.
3. Nom : `ZIONIA Écoute` → **OK**.
4. **Copie le jeton** : il n'est affiché qu'une fois.

## 4. Les réglages

```powershell
copy reglages.exemple.ini reglages.ini
notepad reglages.ini
```

Dans le Bloc-notes :

- `url =` : l'adresse de Home Assistant, **la même que dans ton
  navigateur**, par exemple `http://192.168.68.72`.
- `jeton =` : colle le jeton de l'étape 3.

Enregistre (**Ctrl+S**) et ferme.

`reglages.ini` contient ton jeton : il est exclu de git et ne part jamais
sur GitHub.

## 5. Choisir le micro

```powershell
.venv\Scripts\python zionia_ecoute.py --micros
```

Repère la ligne de ton casque et mets son numéro dans `micro =` de
`reglages.ini`. Laisse vide pour le micro par défaut de Windows.

## 6. Lancer

```powershell
.venv\Scripts\python zionia_ecoute.py
```

Le premier lancement télécharge le modèle du mot d'activation. Ensuite :

```
Home Assistant : http://192.168.68.72  ·  transcription : stt.faster_whisper  ·  agent : conversation.zionia
J'écoute « hey_jarvis ». Ctrl+C pour arrêter.
```

Dis **« Hey Jarvis »**, attends le bip, pose ta question, puis tais-toi.
Le Google Home répond.

Pour la suite, double-clique simplement sur **`lancer.bat`**.

## Démarrer avec Windows *(facultatif)*

1. **Windows + R**, tape `shell:startup`, **Entrée** : un dossier s'ouvre.
2. Dans un autre Explorateur, va dans `D:\zionia-home-assistant\ecoute`.
3. Clic droit sur `lancer.bat` → **Afficher d'autres options** →
   **Créer un raccourci**.
4. Glisse ce raccourci dans le dossier de l'étape 1.

## Quand ça ne marche pas

| Ce qui se passe | Quoi faire |
|---|---|
| Il se déclenche tout seul | Dans `reglages.ini`, monte `seuil` à `0.6` ou `0.7`. |
| Il ne réagit pas au mot | Vérifie le micro (étape 5), puis descends `seuil` à `0.4`. |
| Il coupe au milieu de ta phrase | Monte `silence` à `1.5`. |
| « Home Assistant refuse le jeton » | Recrée un jeton (étape 3). |
| « Impossible de joindre Home Assistant » | Vérifie `url` : la même adresse que dans le navigateur. |
| La réponse s'affiche mais rien ne parle | Choisis l'Enceinte dans les options de l'intégration ZIONIA. |

## « OK ZIONIA » au lieu de « Hey Jarvis »

Les mots fournis sont `hey_jarvis`, `hey_mycroft`, `alexa` et
`hey_rhasspy`. Un mot à toi se fabrique avec l'outil d'entraînement
d'openWakeWord, gratuit, dans Google Colab : on tape le mot, il génère
des milliers d'exemples de voix et produit un fichier `.onnx`, en une
heure environ. Le lien est dans la section *Training New Models* de
https://github.com/dscripka/openWakeWord.

Pose le fichier obtenu dans ce dossier, puis dans `reglages.ini` :

```ini
mot = ok_zionia.onnx
```

L'outil est conçu pour l'anglais. « OK Zionia » se prononce presque
pareil dans les deux langues, mais le résultat est à vérifier à l'usage.

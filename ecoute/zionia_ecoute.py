"""ZIONIA Écoute — parler à ZIONIA sans cliquer.

Tourne sur un ordinateur allumé, avec un micro : celui d'un casque
suffit. Il écoute en permanence le mot d'activation, sur place —
rien ne quitte l'ordinateur avant. Quand il l'entend :

    bip → il enregistre la question jusqu'à ce qu'on se taise → bip
      → Whisper la transcrit             (POST /api/stt/…, dans Home Assistant)
      → ZIONIA y répond                  (POST /api/conversation/process)
      → l'enceinte la dit                (l'option « Enceinte » de l'intégration)

Il ne remplace rien : il fait ce que fait le bouton micro d'Assist,
déclenché par la voix au lieu d'un clic.

USAGE
    python zionia_ecoute.py              écouter
    python zionia_ecoute.py --micros     lister les micros

Réglages : reglages.ini, à côté de ce fichier (voir reglages.exemple.ini).
"""

from __future__ import annotations

import argparse
import configparser
import queue
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import requests

DOSSIER = Path(__file__).resolve().parent

# Ce qu'attendent openWakeWord et Whisper : 16 kHz, mono, 16 bits.
TAUX = 16000
# 80 ms : la taille de bloc recommandée par openWakeWord.
BLOC = 1280
BLOCS_PAR_SECONDE = TAUX / BLOC


# ─────────────────────────────────────────────────────────── Réglages


@dataclass
class Reglages:
    url: str
    jeton: str
    reconnaissance: str
    agent: str
    langue: str
    mot: str
    seuil: float
    micro: str
    silence: float
    duree_max: float
    attente_parole: float


def charger_reglages(chemin: Path) -> Reglages:
    if not chemin.exists():
        sys.exit(
            f"Réglages introuvables : {chemin}\n"
            "Copie reglages.exemple.ini en reglages.ini et remplis-le."
        )

    ini = configparser.ConfigParser(interpolation=None)
    ini.read(chemin, encoding="utf-8")
    ha, ecoute = ini["home_assistant"], ini["ecoute"]

    jeton = ha.get("jeton", "").strip()
    if not jeton:
        sys.exit("Le jeton d'accès est vide dans reglages.ini (section home_assistant).")

    return Reglages(
        url=ha.get("url", "").strip().rstrip("/"),
        jeton=jeton,
        reconnaissance=ha.get("reconnaissance", "").strip(),
        agent=ha.get("agent", "conversation.zionia").strip(),
        langue=ha.get("langue", "fr").strip(),
        mot=ecoute.get("mot", "hey_jarvis").strip(),
        seuil=ecoute.getfloat("seuil", 0.5),
        micro=ecoute.get("micro", "").strip(),
        silence=ecoute.getfloat("silence", 1.0),
        duree_max=ecoute.getfloat("duree_max", 15),
        attente_parole=ecoute.getfloat("attente_parole", 5),
    )


# ─────────────────────────────────────────────────────── Home Assistant


class HomeAssistant:
    """Les deux appels du bouton micro d'Assist : transcrire, puis converser."""

    def __init__(self, url: str, jeton: str) -> None:
        self.url = url
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {jeton}"

    def verifier(self) -> None:
        """Échoue tôt, avec une phrase, plutôt qu'à la première question."""
        try:
            reponse = self.session.get(f"{self.url}/api/", timeout=10)
        except requests.RequestException as erreur:
            sys.exit(f"Impossible de joindre Home Assistant à {self.url} : {erreur}")
        if reponse.status_code == 401:
            sys.exit("Home Assistant refuse le jeton : crées-en un nouveau (voir le README).")
        reponse.raise_for_status()

    def trouver_reconnaissance(self) -> str:
        """Le service de transcription : Whisper s'il y est, sinon le premier."""
        etats = self.session.get(f"{self.url}/api/states", timeout=10).json()
        candidats = [e["entity_id"] for e in etats if e["entity_id"].startswith("stt.")]
        if not candidats:
            sys.exit("Aucune reconnaissance vocale (stt.…) dans Home Assistant. Installe Whisper.")
        whisper = [c for c in candidats if "whisper" in c]
        return (whisper or candidats)[0]

    def transcrire(self, pcm: bytes, entite: str, langue: str) -> str:
        """Le même appel que le bouton micro : du PCM brut, décrit par l'en-tête."""
        reponse = self.session.post(
            f"{self.url}/api/stt/{entite}",
            data=pcm,
            headers={
                "X-Speech-Content": (
                    f"format=wav; codec=pcm; sample_rate={TAUX}; "
                    f"bit_rate=16; channel=1; language={langue}"
                ),
                "Content-Type": "application/octet-stream",
            },
            timeout=60,
        )
        reponse.raise_for_status()
        resultat = reponse.json()
        if resultat.get("result") != "success":
            return ""
        return (resultat.get("text") or "").strip()

    def demander(self, texte: str, agent: str, langue: str) -> str:
        """Pose la question à ZIONIA et renvoie ce qu'Assist aurait dit.

        Vide quand l'intégration fait lire la réponse sur une enceinte :
        c'est elle qui parle, pas nous. Trois minutes, comme
        l'intégration : sur processeur, ZIONIA prend son temps.
        """
        reponse = self.session.post(
            f"{self.url}/api/conversation/process",
            json={"text": texte, "agent_id": agent, "language": langue},
            timeout=190,
        )
        reponse.raise_for_status()
        parole = reponse.json().get("response", {}).get("speech", {})
        return (parole.get("plain", {}).get("speech") or "").strip()


# ──────────────────────────────────────────────────────────────── Audio


def lister_micros() -> None:
    import sounddevice as sd

    for i, appareil in enumerate(sd.query_devices()):
        if appareil["max_input_channels"] > 0:
            print(f"  {i:3d}  {appareil['name']}")
    print("\nMets le numéro, ou une partie du nom, dans « micro = » de reglages.ini.")


def choisir_micro(valeur: str):
    """Un numéro, un bout de nom, ou None pour le micro par défaut de Windows."""
    if not valeur:
        return None
    if valeur.isdigit():
        return int(valeur)

    import sounddevice as sd

    for i, appareil in enumerate(sd.query_devices()):
        if appareil["max_input_channels"] > 0 and valeur.lower() in appareil["name"].lower():
            return i
    sys.exit(f"Aucun micro ne contient « {valeur} ». Liste-les avec : python zionia_ecoute.py --micros")


def ouvrir_micro(appareil) -> tuple[object, queue.Queue]:
    """Ouvre le micro et renvoie le flux et une file de blocs de 80 ms à 16 kHz.

    Beaucoup de micros refusent 16 kHz et n'offrent que 44,1 ou 48 kHz.
    On les ouvre alors à leur fréquence, et on ramène chaque bloc à
    16 kHz ici.
    """
    import sounddevice as sd
    from scipy.signal import resample_poly

    file: queue.Queue = queue.Queue()

    try:
        flux = sd.InputStream(
            samplerate=TAUX, channels=1, dtype="int16", blocksize=BLOC, device=appareil,
            callback=lambda donnees, *_: file.put(donnees[:, 0].copy()),
        )
        flux.start()
        return flux, file
    except sd.PortAudioError:
        pass

    natif = int(sd.query_devices(appareil, "input")["default_samplerate"])
    pgcd = np.gcd(natif, TAUX)
    haut, bas = TAUX // pgcd, natif // pgcd
    reste = np.zeros(0, dtype=np.int16)

    def recevoir(donnees, *_):
        nonlocal reste
        converti = resample_poly(donnees[:, 0].astype(np.float32), haut, bas)
        reste = np.concatenate([reste, np.clip(converti, -32768, 32767).astype(np.int16)])
        while len(reste) >= BLOC:
            file.put(reste[:BLOC])
            reste = reste[BLOC:]

    flux = sd.InputStream(
        samplerate=natif, channels=1, dtype="int16",
        blocksize=int(BLOC * natif / TAUX), device=appareil, callback=recevoir,
    )
    flux.start()
    print(f"Micro ouvert à {natif} Hz, ramené à {TAUX} Hz.")
    return flux, file


def bip(frequence: float) -> None:
    """Un bip court : aigu, j'écoute ; grave, c'est noté."""
    import sounddevice as sd

    t = np.arange(int(0.12 * 44100)) / 44100
    onde = 0.25 * np.sin(2 * np.pi * frequence * t) * np.hanning(len(t))
    sd.play(onde.astype(np.float32), 44100)
    sd.wait()


def vider(file: queue.Queue) -> None:
    """Jette ce que le micro a capté pendant qu'on ne l'écoutait pas."""
    while True:
        try:
            file.get_nowait()
        except queue.Empty:
            return


# ────────────────────────────────────────────────────────── La question


def enregistrer_question(lire_bloc, est_parole, reglages: Reglages) -> bytes | None:
    """Enregistre jusqu'à un silence, après que la parole a commencé.

    `lire_bloc` rend le bloc suivant ; `est_parole` dit s'il contient
    de la voix. Rend le PCM 16 bits, ou None si personne n'a parlé.

    Le silence se mesure en blocs consécutifs sans voix — une pause
    pour respirer au milieu d'une phrase n'y suffit pas.
    """
    blocs: list[np.ndarray] = []
    parle = False
    muets = 0
    silence_max = int(reglages.silence * BLOCS_PAR_SECONDE)
    attente_max = int(reglages.attente_parole * BLOCS_PAR_SECONDE)
    total_max = int(reglages.duree_max * BLOCS_PAR_SECONDE)

    for n in range(total_max):
        bloc = lire_bloc()
        blocs.append(bloc)

        if est_parole(bloc):
            parle = True
            muets = 0
        elif parle:
            muets += 1
            if muets >= silence_max:
                break
        elif n >= attente_max:
            return None

    if not parle:
        return None
    return np.concatenate(blocs).astype("<i2").tobytes()


# ─────────────────────────────────────────────────────────── Principal


def charger_mot(mot: str):
    """Un mot fourni (« hey_jarvis ») ou un modèle à soi (« ok_zionia.onnx »).

    ONNX et non TFLite : TFLite n'existe pas sous Windows.
    """
    from openwakeword import utils
    from openwakeword.model import Model

    if mot.endswith(".onnx"):
        chemin = Path(mot) if Path(mot).is_absolute() else DOSSIER / mot
        if not chemin.exists():
            sys.exit(f"Modèle introuvable : {chemin}")
        utils.download_models(model_names=["__aucun__"])  # mel + embedding seulement
        return Model(wakeword_models=[str(chemin)], inference_framework="onnx")

    utils.download_models(model_names=[mot])
    return Model(wakeword_models=[mot], inference_framework="onnx")


def principal() -> None:
    parseur = argparse.ArgumentParser(description="ZIONIA Écoute")
    parseur.add_argument("--micros", action="store_true", help="lister les micros et quitter")
    parseur.add_argument("--reglages", default=str(DOSSIER / "reglages.ini"))
    arguments = parseur.parse_args()

    if arguments.micros:
        lister_micros()
        return

    reglages = charger_reglages(Path(arguments.reglages))

    ha = HomeAssistant(reglages.url, reglages.jeton)
    ha.verifier()
    stt = reglages.reconnaissance or ha.trouver_reconnaissance()

    from openwakeword.vad import VAD

    modele = charger_mot(reglages.mot)
    vad = VAD()
    flux, file = ouvrir_micro(choisir_micro(reglages.micro))

    print(f"Home Assistant : {reglages.url}  ·  transcription : {stt}  ·  agent : {reglages.agent}")
    print(f"J'écoute « {reglages.mot} ». Ctrl+C pour arrêter.")

    try:
        while True:
            bloc = file.get()
            scores = modele.predict(bloc)
            if max(scores.values()) < reglages.seuil:
                continue

            bip(880)
            vider(file)
            print("\n… je t'écoute")

            pcm = enregistrer_question(
                file.get, lambda b: vad.predict(b) >= 0.5, reglages
            )
            bip(440)

            if pcm is None:
                print("   (rien entendu)")
            else:
                try:
                    texte = ha.transcrire(pcm, stt, reglages.langue)
                    print(f"   toi    : {texte or '(rien compris)'}")
                    if texte:
                        debut = time.monotonic()
                        reponse = ha.demander(texte, reglages.agent, reglages.langue)
                        duree = time.monotonic() - debut
                        print(f"   ZIONIA : {reponse or '(lue sur l’enceinte)'}  [{duree:.0f} s]")
                except requests.RequestException as erreur:
                    print(f"   Erreur avec Home Assistant : {erreur}")

            # Sans ça, la fin du mot d'activation — encore dans la
            # mémoire du modèle — le redéclencherait aussitôt.
            modele.reset()
            vider(file)
    except KeyboardInterrupt:
        print("\nArrêt.")
    finally:
        flux.stop()


if __name__ == "__main__":
    principal()

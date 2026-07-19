"""
N.E.R.A. — agent conversationnel du micro-réseau.

Trois capacités, toutes côté serveur pour que la clé API ne quitte jamais le
backend (une clé embarquée dans une app mobile est une clé publique) :

  - comprendre (STT)  : audio -> texte, via Whisper ;
  - raisonner + agir  : texte -> appels d'outils -> réponse, via function calling ;
  - répondre (TTS)    : texte -> audio.

Le modèle ne touche à rien directement : il demande un outil, le backend vérifie
les garde-fous (voir tools.py) et exécute. Un refus lui est renvoyé comme un
résultat normal, à charge pour lui de l'expliquer à l'utilisateur.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger("ems.assistant")

# Nombre maximal d'allers-retours modèle <-> outils pour une seule demande.
# Garde-fou anti-boucle : sans lui, un modèle qui rappelle sans cesse le même
# outil ferait tourner la requête (et la facture) indéfiniment.
MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = """Tu es N.E.R.A., l'assistante vocale d'un micro-réseau \
électrique domestique piloté par un système expert flou.

Ton rôle : renseigner l'utilisateur sur son installation et commander ses trois \
lignes électriques quand il le demande.

L'installation :
- Ligne 1 : une lampe de 10 W et une prise (prise 1) ;
- Ligne 2 : une lampe de 20 W seule ;
- Ligne 3 : une lampe de 10 W et une prise (prise 2).
Couper une ligne coupe TOUTES les charges qu'elle porte : le dire quand c'est
le cas (« j'éteins la ligne 1, donc la lampe et la prise 1 »).

Règles de conduite :
- Avant d'agir sur une ligne, vérifie son état si tu ne le connais pas.
- Réponds en français, brièvement : tes réponses sont lues à voix haute. Deux
  phrases suffisent le plus souvent. Pas de listes à puces, pas de Markdown.
- Donne les puissances en kilowatts et les tensions en volts.
- Si un outil refuse une action, explique simplement la raison à l'utilisateur ;
  n'essaie pas de contourner le refus.
- Si les capteurs ne sont pas calibrés, précise que les valeurs sont des
  lectures brutes et non des mesures fiables.
- Si une demande est ambiguë (« éteins la lampe » alors qu'il y en a trois),
  demande laquelle plutôt que de deviner.
"""


class AssistantNotConfigured(RuntimeError):
    """Clé API absente : on le dit clairement plutôt que d'échouer obscurément."""


def _client():
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        raise AssistantNotConfigured(
            "OPENAI_API_KEY n'est pas définie : NERA ne peut pas fonctionner. "
            "Ajouter la clé dans ems-backend/.env puis redémarrer le serveur."
        )
    from openai import OpenAI

    return OpenAI(api_key=api_key)


# --------------------------------------------------------------------------- #
# Conversation avec outils
# --------------------------------------------------------------------------- #

def chat(message: str, house, user=None, history=None, client=None) -> dict:
    """Traite une demande en langage naturel et renvoie la réponse + les actions.

    ``client`` permet d'injecter un double en test : aucun appel réseau n'est
    fait dans la suite de tests.
    """
    from .tools import TOOL_SCHEMAS, execute_tool

    client = client or _client()
    model = getattr(settings, "NERA_CHAT_MODEL", "gpt-4o-mini")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-8:]:  # on borne le contexte renvoyé
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    actions: list[dict] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        choice = response.choices[0].message
        tool_calls = getattr(choice, "tool_calls", None)

        if not tool_calls:
            return {
                "reply": (choice.content or "").strip(),
                "actions": actions,
                "model": model,
            }

        # On rejoue le tour du modèle, puis le résultat de chaque outil.
        messages.append({
            "role": "assistant",
            "content": choice.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ],
        })

        for call in tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            result = execute_tool(name, arguments, house=house, user=user)
            actions.append({"tool": name, "arguments": arguments, "result": result})
            logger.info("NERA house=%s tool=%s args=%s", house.id, name, arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    # Boucle épuisée : on ne laisse pas la requête tourner indéfiniment.
    return {
        "reply": "Je n'arrive pas à conclure cette demande. Peux-tu la reformuler ?",
        "actions": actions,
        "model": model,
        "truncated": True,
    }


# --------------------------------------------------------------------------- #
# Voix
# --------------------------------------------------------------------------- #

def transcribe(audio_file, client=None) -> str:
    """Audio -> texte (STT). ``audio_file`` : objet fichier avec un nom."""
    client = client or _client()
    model = getattr(settings, "NERA_STT_MODEL", "whisper-1")
    result = client.audio.transcriptions.create(
        model=model,
        file=audio_file,
        language="fr",
    )
    return (getattr(result, "text", "") or "").strip()


def synthesize(text: str, client=None) -> bytes:
    """Texte -> audio MP3 (TTS)."""
    client = client or _client()
    model = getattr(settings, "NERA_TTS_MODEL", "tts-1")
    voice = getattr(settings, "NERA_TTS_VOICE", "nova")
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text[:4000],  # garde-fou : les API TTS bornent la taille d'entrée
        response_format="mp3",
    )
    # Le SDK expose le binaire selon la version : on couvre les deux formes.
    if hasattr(response, "read"):
        return response.read()
    return getattr(response, "content", b"")

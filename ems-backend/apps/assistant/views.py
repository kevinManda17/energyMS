"""Endpoints de N.E.R.A. : texte, voix et synthèse vocale."""
from __future__ import annotations

import logging

from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from . import agent

logger = logging.getLogger("ems.assistant")

# Limite de taille d'un enregistrement vocal accepté. Une commande domotique
# dure quelques secondes : au-delà, c'est une erreur ou un abus, et chaque
# transcription est facturée.
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 Mo


def _get_house_or_403(user, house_id):
    qs = House.objects.all()
    if user.is_authenticated and not user.is_admin:
        qs = qs.filter(owner=user)
    house = qs.filter(pk=house_id).first()
    if house is None:
        raise PermissionDenied("Micro-réseau introuvable ou non accessible.")
    return house


class _NeraBaseView(APIView):
    """Facteur commun : résolution de la maison et gestion de la clé absente."""

    def _house(self, request):
        house_id = request.data.get("house") or request.query_params.get("house")
        if not house_id:
            raise PermissionDenied("Le paramètre 'house' est requis.")
        return _get_house_or_403(request.user, house_id)

    @staticmethod
    def _not_configured(exc):
        # 503 plutôt que 500 : le service est indisponible par configuration,
        # ce n'est pas un plantage. L'interface peut l'afficher tel quel.
        return Response({"detail": str(exc)}, status=503)


class NeraChatView(_NeraBaseView):
    """POST /api/nera/chat/  {house, message, history?}

    Conversation en texte. Renvoie la réponse de NERA et la liste des actions
    réellement exécutées (utile pour l'affichage et la traçabilité).
    """

    def post(self, request):
        house = self._house(request)
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "Le champ 'message' est vide."}, status=400)
        history = request.data.get("history") or []

        try:
            result = agent.chat(message, house=house, user=request.user,
                                history=history)
        except agent.AssistantNotConfigured as exc:
            return self._not_configured(exc)
        except Exception:
            logger.exception("NERA chat a échoué (house=%s)", house.id)
            return Response(
                {"detail": "NERA n'a pas pu traiter la demande. Réessayer."},
                status=502,
            )
        return Response(result)


class NeraVoiceView(_NeraBaseView):
    """POST /api/nera/voice/  (multipart : house, audio, speak?)

    Chaîne vocale complète : transcription -> raisonnement/action -> réponse.
    `speak=true` renvoie en plus la réponse audio encodée en base64, pour que le
    client la joue sans second appel.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        house = self._house(request)
        audio = request.FILES.get("audio")
        if audio is None:
            return Response({"detail": "Fichier 'audio' manquant."}, status=400)
        if audio.size > MAX_AUDIO_BYTES:
            return Response(
                {"detail": "Enregistrement trop long (10 Mo maximum)."}, status=413
            )

        try:
            transcript = agent.transcribe(audio)
            if not transcript:
                return Response({
                    "transcript": "",
                    "reply": "Je n'ai rien entendu. Peux-tu répéter ?",
                    "actions": [],
                })
            result = agent.chat(transcript, house=house, user=request.user,
                                history=request.data.get("history") or [])
            result["transcript"] = transcript

            if str(request.data.get("speak", "")).lower() in ("1", "true", "yes"):
                import base64
                audio_bytes = agent.synthesize(result["reply"])
                result["audio_base64"] = base64.b64encode(audio_bytes).decode()
                result["audio_format"] = "mp3"
        except agent.AssistantNotConfigured as exc:
            return self._not_configured(exc)
        except Exception:
            logger.exception("NERA voice a échoué (house=%s)", house.id)
            return Response(
                {"detail": "NERA n'a pas pu traiter l'enregistrement."}, status=502
            )
        return Response(result)


class NeraSpeakView(_NeraBaseView):
    """POST /api/nera/speak/  {text}  ->  audio/mpeg

    Synthèse seule, utile pour relire un message existant (une alerte, une
    recommandation du système expert) sans repasser par le modèle.
    """

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Le champ 'text' est vide."}, status=400)
        try:
            audio = agent.synthesize(text)
        except agent.AssistantNotConfigured as exc:
            return self._not_configured(exc)
        except Exception:
            logger.exception("NERA TTS a échoué")
            return Response({"detail": "Synthèse vocale indisponible."}, status=502)
        return HttpResponse(audio, content_type="audio/mpeg")

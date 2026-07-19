from django.urls import path

from .views import NeraChatView, NeraSpeakView, NeraVoiceView

urlpatterns = [
    # Conversation en texte.
    path("nera/chat/", NeraChatView.as_view(), name="nera-chat"),
    # Chaîne vocale complète : audio -> transcription -> action -> réponse.
    path("nera/voice/", NeraVoiceView.as_view(), name="nera-voice"),
    # Synthèse vocale seule (relire un texte existant).
    path("nera/speak/", NeraSpeakView.as_view(), name="nera-speak"),
]

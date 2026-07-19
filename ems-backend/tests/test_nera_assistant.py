"""N.E.R.A. — outils, garde-fous et conversation.

Aucun appel réseau : le client OpenAI est simulé. Ces tests vérifient ce que
NOUS contrôlons (les garde-fous et l'exécution des outils), pas le modèle.
"""
import json
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.assistant import agent, tools
from apps.devices.models import Equipment, RelayState
from apps.houses.models import House

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def house():
    user = User.objects.create_user("nera", "nera@x.com", "pass12345")
    return House.objects.create(owner=user, name="Prototype")


@pytest.fixture
def auth_client(house):
    client = APIClient()
    client.force_authenticate(house.owner)
    return client, house


# --------------------------------------------------------------------------- #
# Double du client OpenAI
# --------------------------------------------------------------------------- #

def _tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


class FakeOpenAI:
    """Rejoue une séquence de réponses préparées, comme le ferait l'API."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = self._scripted.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _reply(text):
    return SimpleNamespace(content=text, tool_calls=None)


def _calls_then_reply(name, arguments, text):
    return [
        SimpleNamespace(content=None, tool_calls=[_tool_call(name, arguments)]),
        _reply(text),
    ]


# --------------------------------------------------------------------------- #
# Outils : lecture
# --------------------------------------------------------------------------- #

def test_get_lines_state_lists_loads_per_line(house):
    RelayState.objects.create(house=house)
    Equipment.objects.create(house=house, name="Lampe L1", relay_line=1,
                             load_type="lamp", priority="NORMAL")
    Equipment.objects.create(house=house, name="Prise 1", relay_line=1,
                             load_type="socket", priority="NON_CRITICAL")

    state = tools.get_lines_state(house)
    line1 = next(l for l in state["lignes"] if l["ligne"] == 1)
    assert line1["allumee"] is True
    assert {c["nom"] for c in line1["charges"]} == {"Lampe L1", "Prise 1"}


def test_set_line_switches_the_relay(house):
    RelayState.objects.create(house=house)
    result = tools.set_line(house, line=2, on=False)
    assert result["allumee"] is False
    assert RelayState.objects.get(house=house).line2 is False


# --------------------------------------------------------------------------- #
# Garde-fous
# --------------------------------------------------------------------------- #

def test_voice_control_refused_in_auto_mode(house):
    """En mode automatique, c'est l'expert qui pilote : la voix ne contourne pas."""
    RelayState.objects.create(house=house,
                              control_mode=RelayState.ControlMode.AUTO)
    result = tools.execute_tool("set_line", {"line": 1, "on": False}, house=house)
    assert "refus" in result
    assert "automatique" in result["refus"].lower()
    assert RelayState.objects.get(house=house).line1 is True  # rien coupé


def test_critical_line_cannot_be_cut_by_voice(house):
    RelayState.objects.create(house=house)
    Equipment.objects.create(house=house, name="Respirateur", relay_line=3,
                             priority="CRITICAL", status="ACTIVE")
    result = tools.execute_tool("set_line", {"line": 3, "on": False}, house=house)
    assert "refus" in result
    assert RelayState.objects.get(house=house).line3 is True


def test_critical_line_can_still_be_turned_on(house):
    """Le garde-fou protège de la COUPURE, il n'empêche pas d'alimenter."""
    RelayState.objects.create(house=house, line3=False)
    Equipment.objects.create(house=house, name="Respirateur", relay_line=3,
                             priority="CRITICAL", status="ACTIVE")
    result = tools.execute_tool("set_line", {"line": 3, "on": True}, house=house)
    assert "refus" not in result
    assert RelayState.objects.get(house=house).line3 is True


def test_all_off_preserves_critical_lines(house):
    RelayState.objects.create(house=house)
    Equipment.objects.create(house=house, name="Respirateur", relay_line=2,
                             priority="CRITICAL", status="ACTIVE")
    result = tools.execute_tool("set_all_lines", {"on": False}, house=house)
    state = RelayState.objects.get(house=house)
    assert state.line1 is False and state.line3 is False
    assert state.line2 is True                      # ligne critique préservée
    assert result["lignes_preservees"] == [2]


def test_unknown_line_is_rejected(house):
    RelayState.objects.create(house=house)
    result = tools.execute_tool("set_line", {"line": 7, "on": True}, house=house)
    assert "refus" in result


def test_unknown_tool_is_reported_not_crashing(house):
    result = tools.execute_tool("rm_rf", {}, house=house)
    assert "erreur" in result


# --------------------------------------------------------------------------- #
# Conversation
# --------------------------------------------------------------------------- #

def test_chat_executes_the_requested_tool(house):
    RelayState.objects.create(house=house)
    fake = FakeOpenAI(_calls_then_reply(
        "set_line", {"line": 2, "on": False}, "C'est fait, j'ai éteint la ligne 2."
    ))

    result = agent.chat("éteins la lampe de 20 watts", house=house, client=fake)

    assert "éteint" in result["reply"]
    assert result["actions"][0]["tool"] == "set_line"
    assert RelayState.objects.get(house=house).line2 is False


def test_chat_relays_a_refusal_to_the_model(house):
    """Un refus d'outil doit revenir au modèle pour qu'il l'explique."""
    RelayState.objects.create(house=house,
                              control_mode=RelayState.ControlMode.AUTO)
    fake = FakeOpenAI(_calls_then_reply(
        "set_line", {"line": 1, "on": False},
        "Impossible : le réseau est en mode automatique."
    ))

    result = agent.chat("coupe la ligne 1", house=house, client=fake)

    tool_message = next(m for m in fake.calls[-1]["messages"] if m.get("role") == "tool")
    assert "refus" in tool_message["content"]
    assert result["actions"][0]["result"]["refus"]


def test_chat_stops_after_too_many_tool_rounds(house):
    """Un modèle qui boucle ne doit pas faire tourner la requête sans fin."""
    RelayState.objects.create(house=house)
    looping = [
        SimpleNamespace(content=None,
                        tool_calls=[_tool_call("get_lines_state", {}, f"c{i}")])
        for i in range(agent.MAX_TOOL_ROUNDS + 2)
    ]
    fake = FakeOpenAI(looping)

    result = agent.chat("bonjour", house=house, client=fake)

    assert result.get("truncated") is True
    assert len(result["actions"]) == agent.MAX_TOOL_ROUNDS


def test_chat_without_tools_returns_plain_answer(house):
    fake = FakeOpenAI([_reply("Bonjour, je suis NERA.")])
    result = agent.chat("bonjour", house=house, client=fake)
    assert result["reply"] == "Bonjour, je suis NERA."
    assert result["actions"] == []


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #

def test_chat_endpoint_requires_a_message(auth_client):
    client, house = auth_client
    resp = client.post("/api/nera/chat/", {"house": house.id, "message": "  "},
                       format="json")
    assert resp.status_code == 400


def test_endpoint_reports_missing_api_key_as_unavailable(auth_client, settings):
    """Sans clé, on renvoie 503 et un message clair — pas une erreur 500."""
    settings.OPENAI_API_KEY = ""
    client, house = auth_client
    resp = client.post("/api/nera/chat/",
                       {"house": house.id, "message": "allume la ligne 1"},
                       format="json")
    assert resp.status_code == 503
    assert "OPENAI_API_KEY" in resp.data["detail"]


def test_user_cannot_drive_another_persons_microgrid(auth_client):
    client, _house = auth_client
    intruder = User.objects.create_user("eve", "eve@x.com", "pass12345")
    other = House.objects.create(owner=intruder, name="Chez Eve")
    resp = client.post("/api/nera/chat/",
                       {"house": other.id, "message": "éteins tout"},
                       format="json")
    assert resp.status_code in (403, 404)

"""
Outils que N.E.R.A. peut appeler (function calling).

Chaque outil est décrit au modèle par un schéma JSON, puis exécuté ICI, côté
serveur. Le modèle ne touche jamais directement à la base ni aux relais : il
demande, on vérifie, on exécute. Toute la sécurité est donc dans ce fichier.

GARDE-FOUS (non négociables)
1. Mode de contrôle respecté. NERA parle au nom de l'utilisateur : elle agit
   donc comme une commande MANUELLE. En mode AUTO, où l'interface désactive
   déjà les interrupteurs, NERA refuse aussi — sinon la voix contournerait le
   système expert.
2. Une ligne portant une charge CRITIQUE n'est jamais coupée sur ordre vocal.
   La reconnaissance vocale se trompe ; couper un équipement vital sur un
   « éteins tout » mal transcrit n'est pas acceptable.
3. Périmètre limité à une maison, celle passée par la vue (jamais choisie par
   le modèle) : NERA ne peut pas agir sur le micro-réseau d'autrui.
4. Aucun outil destructif au-delà des relais : pas de suppression, pas de
   modification de calibration, pas d'accès aux utilisateurs.
"""
from __future__ import annotations

from django.utils import timezone

LINE_FIELDS = {1: "line1", 2: "line2", 3: "line3"}


# --------------------------------------------------------------------------- #
# Schémas exposés au modèle
# --------------------------------------------------------------------------- #

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_lines_state",
            "description": (
                "État actuel des trois lignes électriques : allumée/éteinte, "
                "charges rattachées, mode de contrôle du micro-réseau. "
                "À appeler avant toute action pour savoir ce qui est déjà allumé."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_line",
            "description": (
                "Allume ou éteint UNE ligne électrique. La ligne 1 porte une "
                "lampe 10 W et une prise, la ligne 2 une lampe 20 W seule, la "
                "ligne 3 une lampe 10 W et une prise. Couper une ligne coupe "
                "toutes les charges qu'elle porte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "line": {
                        "type": "integer",
                        "enum": [1, 2, 3],
                        "description": "Numéro de la ligne (1, 2 ou 3).",
                    },
                    "on": {
                        "type": "boolean",
                        "description": "true pour allumer, false pour éteindre.",
                    },
                },
                "required": ["line", "on"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_all_lines",
            "description": "Allume ou éteint les trois lignes d'un coup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "on": {
                        "type": "boolean",
                        "description": "true pour tout allumer, false pour tout éteindre.",
                    }
                },
                "required": ["on"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_measurements",
            "description": (
                "Dernières mesures du micro-réseau : tension (V), courant (A), "
                "puissance actuelle (kW), état de charge batterie. Préciser si "
                "les capteurs ne sont pas calibrés."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expert_decision",
            "description": (
                "Dernière décision du système expert flou : ce qu'il recommande "
                "et pourquoi (niveau de risque, délestage conseillé)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# --------------------------------------------------------------------------- #
# Exécution
# --------------------------------------------------------------------------- #

class ToolError(Exception):
    """Refus explicite, renvoyé au modèle pour qu'il l'explique à l'utilisateur."""


def _loads_by_line(house):
    from apps.devices.models import Equipment

    result: dict[int, list] = {1: [], 2: [], 3: []}
    rows = Equipment.objects.filter(
        house=house, relay_line__isnull=False
    ).values_list("relay_line", "name", "priority")
    for line, name, priority in rows:
        if line in result:
            result[line].append({"nom": name, "priorite": priority})
    return result


def _critical_lines(house) -> set[int]:
    from apps.devices.models import Equipment

    return set(
        Equipment.objects.filter(
            house=house,
            relay_line__isnull=False,
            priority=Equipment.Priority.CRITICAL,
            status=Equipment.Status.ACTIVE,
        ).values_list("relay_line", flat=True)
    )


def _relay_state(house):
    from apps.devices.models import RelayState

    state, _ = RelayState.objects.get_or_create(house=house)
    return state


def get_lines_state(house, user=None):
    state = _relay_state(house)
    loads = _loads_by_line(house)
    return {
        "mode_de_controle": state.control_mode,
        "lignes": [
            {
                "ligne": n,
                "allumee": getattr(state, LINE_FIELDS[n]),
                "charges": loads[n],
            }
            for n in (1, 2, 3)
        ],
    }


def _guard_manual_control(state):
    """NERA agit au nom de l'utilisateur : interdite quand l'humain ne commande pas."""
    from apps.devices.models import RelayState

    if state.control_mode == RelayState.ControlMode.AUTO:
        raise ToolError(
            "Le micro-réseau est en mode automatique : c'est le système expert "
            "qui pilote les lignes. Repasser en mode manuel pour commander à la "
            "voix."
        )


def set_line(house, line: int, on: bool, user=None):
    line = int(line)
    if line not in LINE_FIELDS:
        raise ToolError("Ligne inconnue : seules les lignes 1, 2 et 3 existent.")

    state = _relay_state(house)
    _guard_manual_control(state)

    if not on and line in _critical_lines(house):
        raise ToolError(
            f"La ligne {line} alimente une charge critique : elle ne peut pas "
            "être coupée à la voix. Le faire manuellement dans l'application si "
            "c'est vraiment voulu."
        )

    field = LINE_FIELDS[line]
    setattr(state, field, bool(on))
    state.last_commanded_at = timezone.now()
    if user is not None and getattr(user, "is_authenticated", False):
        state.updated_by = user
    state.save(update_fields=[field, "last_commanded_at", "updated_by", "updated_at"])

    return {
        "ligne": line,
        "allumee": bool(on),
        "charges_concernees": _loads_by_line(house)[line],
        "note": "Appliqué au prochain relevé du nœud (environ 3 secondes).",
    }


def set_all_lines(house, on: bool, user=None):
    state = _relay_state(house)
    _guard_manual_control(state)

    critical = _critical_lines(house)
    if not on and critical:
        # On éteint ce qu'on peut, on préserve le critique, et on le dit.
        touched = [n for n in (1, 2, 3) if n not in critical]
    else:
        touched = [1, 2, 3]

    for n in touched:
        setattr(state, LINE_FIELDS[n], bool(on))
    state.last_commanded_at = timezone.now()
    if user is not None and getattr(user, "is_authenticated", False):
        state.updated_by = user
    state.save(update_fields=["line1", "line2", "line3", "last_commanded_at",
                              "updated_by", "updated_at"])

    result = {"lignes_modifiees": touched, "allumees": bool(on)}
    if not on and critical:
        result["lignes_preservees"] = sorted(critical)
        result["note"] = (
            "Les lignes portant une charge critique ont été laissées allumées."
        )
    return result


def get_measurements(house, user=None):
    from apps.devices.models import Sensor
    from apps.measurements.models import Measurement

    wanted = ["voltage", "current", "consumption", "battery_soc"]
    latest = {}
    for mtype in wanted:
        row = (
            Measurement.objects.filter(house=house, measurement_type=mtype)
            .order_by("-timestamp")
            .first()
        )
        if row:
            latest[mtype] = {"valeur": round(row.value, 4), "unite": row.unit,
                             "horodatage": row.timestamp.isoformat()}

    uncalibrated = Sensor.objects.filter(house=house, is_active=True).exclude(
        calibration_status="calibrated"
    ).count()

    payload = {"mesures": latest or "aucune mesure enregistrée"}
    if uncalibrated:
        payload["avertissement"] = (
            f"{uncalibrated} capteur(s) ne sont pas calibrés : les valeurs sont "
            "des lectures brutes, pas des volts/ampères réels."
        )
    return payload


def get_expert_decision(house, user=None):
    from apps.fuzzy_engine.models import Decision

    decision = Decision.objects.filter(house=house).order_by("-created_at").first()
    if decision is None:
        return {"decision": "aucune décision enregistrée pour l'instant"}
    return {
        "decision": decision.decision_label or decision.decision_code,
        "mode_execution": decision.execution_mode,
        "niveau_alerte": decision.alert_level,
        "score_risque": round(decision.risk_score, 1),
        "explication": decision.explanation[:400],
        "horodatage": decision.created_at.isoformat(),
    }


TOOL_IMPLEMENTATIONS = {
    "get_lines_state": get_lines_state,
    "set_line": set_line,
    "set_all_lines": set_all_lines,
    "get_measurements": get_measurements,
    "get_expert_decision": get_expert_decision,
}


def execute_tool(name: str, arguments: dict, house, user=None) -> dict:
    """Exécute un outil demandé par le modèle. Ne lève jamais : un refus est une
    réponse, que le modèle doit pouvoir reformuler à l'utilisateur."""
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if impl is None:
        return {"erreur": f"Outil inconnu : {name}"}
    try:
        return impl(house=house, user=user, **(arguments or {}))
    except ToolError as exc:
        return {"refus": str(exc)}
    except TypeError as exc:
        return {"erreur": f"Paramètres invalides pour {name} : {exc}"}

"""
Énumérations de référence servies par l'API.

LE DÉFAUT CORRIGÉ : les libellés des priorités, des codes de décision, des
modes d'exécution et des niveaux d'alerte étaient ÉCRITS EN DUR dans le code
du web et du mobile. Trois listes pour la même énumération — la base, le web,
le mobile — et elles ne coïncidaient pas.

C'est l'origine du défaut d'affichage des priorités : l'interface montrait
« prioritaire » là où la base disait `IMPORTANT`, et une valeur qu'elle ne
connaissait pas tombait dans le vide. Ajouter un niveau de priorité obligeait à
modifier trois dépôts, et en oublier un le faisait disparaître de l'affichage
sans erreur.

Après correction, un ajout se propage sans toucher au web ni au mobile.

L'ORDRE COMPTE. Les priorités sont servies du plus délestable au plus protégé,
selon le rang du moteur : une interface qui affiche la liste telle quelle
présente donc les niveaux dans l'ordre qui a un sens physique.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.devices.models import Equipment, IoTNode, Priority
from apps.fuzzy_engine.core.decision_mapper import DECISION_LABELS
from apps.measurements.models import Quantity, Source, unit_for


def _choices(enum) -> list[dict]:
    return [{"value": v, "label": label} for v, label in enum.choices]


class ReferenceView(APIView):
    """GET /api/reference/ — toutes les énumérations, en une requête.

    Une seule requête plutôt qu'une par énumération : les interfaces en ont
    besoin au démarrage, et six allers-retours pour afficher un formulaire
    seraient six occasions d'échouer à moitié.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "priorities": [
                {"value": p.value, "label": p.label}
                for p in Priority.ordered()
            ],
            "decision_codes": [
                {"value": code, "label": label}
                for code, label in DECISION_LABELS.items()
            ],
            "execution_modes": [
                {"value": "AUTOMATIC", "label": "Automatique"},
                {"value": "RECOMMENDATION", "label": "Recommandation"},
                {"value": "BLOCKED", "label": "Bloquée"},
            ],
            "alert_levels": [
                {"value": "NONE", "label": "Aucune"},
                {"value": "INFO", "label": "Information"},
                {"value": "WARNING", "label": "Avertissement"},
                {"value": "CRITICAL", "label": "Critique"},
            ],
            "equipment_statuses": _choices(Equipment.Status),
            "load_types": _choices(Equipment.LoadType),
            "control_modes": _choices(IoTNode.ControlMode),
            "node_types": _choices(IoTNode.NodeType),
            # Les grandeurs portent leur unité : l'interface n'a plus à la
            # deviner ni à la stocker de son côté.
            "quantities": [
                {"value": q.value, "label": q.label, "unit": unit_for(q.value)}
                for q in Quantity
            ],
            "measurement_sources": _choices(Source),
        })

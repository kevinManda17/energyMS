"""
Calibration des capteurs : calcul du coefficient et validation croisée.

Principe (voir docs/SENSORS_AND_CALIBRATION.md) :

    valeur_physique = valeur_brute_rms × calibration_factor + calibration_offset

Le système ne cherche pas à produire une valeur « jolie » : il produit la valeur
réellement mesurée, corrigée par un coefficient fiable. Aucune valeur n'est donc
plafonnée, arrondie vers une cible, ni harmonisée entre lignes.

VALIDATION CROISÉE — l'idée centrale
Des capteurs de même modèle, alimentés pareil, lus sur des entrées ADC
équivalentes et mesurant la même source AC doivent avoir des coefficients
*proches*. Proches, pas identiques : les potentiomètres diffèrent, et les lignes
fluctuent réellement. On compare donc chaque coefficient à la référence de ses
semblables et on SIGNALE l'anomalie — on ne la corrige jamais automatiquement.

    écart_% = |CAL_x − médiane| / médiane × 100
    écart_% > SUSPECT_DEVIATION_PERCENT  ->  capteur marqué « suspect »

Pourquoi la MÉDIANE et non la moyenne : un seul coefficient aberrant tire la
moyenne à lui et fait alors dépasser le seuil aux capteurs SAINS. Exemple réel
(126.5, 129.2, 300.0) : la moyenne vaut 185.2, et les trois capteurs sont
déclarés suspects — y compris les deux corrects. La médiane vaut 129.2 : seul
le capteur à 300.0 est signalé, ce qui est le comportement attendu. La moyenne
reste calculée et renvoyée, mais à titre informatif uniquement.

Un capteur suspect ne veut pas dire « mauvaise valeur à masquer » : il veut dire
« va vérifier le câblage, l'alimentation, le GND commun, le potentiomètre ou
l'entrée ADC ». C'est un outil de diagnostic, pas un correcteur.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

# Au-delà de cet écart à la MÉDIANE des capteurs du même type, on considère
# qu'un coefficient trahit un problème de montage plutôt qu'une dispersion
# normale entre composants.
SUSPECT_DEVIATION_PERCENT = 15.0

# En dessous de deux capteurs comparables, la référence n'a pas de sens :
# on ne peut rien conclure et on ne marque personne comme suspect.
MIN_PEERS_FOR_COMPARISON = 2


@dataclass
class CalibrationProposal:
    """Coefficient proposé à l'utilisateur — jamais appliqué sans confirmation."""

    sensor_code: str
    raw_value: float
    reference_value: float
    proposed_factor: float
    current_factor: float

    def to_dict(self) -> dict:
        return {
            "sensor_code": self.sensor_code,
            "raw_value": self.raw_value,
            "reference_value": self.reference_value,
            "proposed_factor": round(self.proposed_factor, 6),
            "current_factor": self.current_factor,
        }


def propose_factor(raw_value: float, reference_value: float,
                   turns: int = 1) -> float:
    """Coefficient à appliquer pour qu'une valeur brute donne la référence.

    ``turns`` : nombre de tours du fil de phase dans le tore du capteur de
    courant. Faire N tours multiplie le courant vu par N ; la référence de
    calibration devient donc N × I_réel. Après calibration, remettre un seul
    passage. (Sans objet pour la tension : laisser turns=1.)
    """
    if raw_value in (None, 0) or reference_value is None:
        raise ValueError(
            "Valeur brute nulle ou absente : impossible de calculer un "
            "coefficient. Vérifier que le capteur remonte bien une mesure."
        )
    return (reference_value * turns) / raw_value


def deviation_percent(factor: float, reference: float) -> float:
    """Écart relatif d'un coefficient à la référence de ses semblables, en %."""
    if not reference:
        return 0.0
    return abs(factor - reference) / abs(reference) * 100.0


def evaluate_group(sensors) -> dict[int, dict]:
    """Compare les coefficients d'un groupe de capteurs comparables.

    Renvoie {sensor_id: {status, deviation_percent, reference_factor,
    mean_factor, peers}}. Seuls les capteurs réellement calibrés servent de
    référence : inclure les coefficients à 1.0 (non calibrés) fausserait la
    comparaison et ferait passer les capteurs corrects pour suspects.
    """
    calibrated = [s for s in sensors if s.is_calibrated]
    results: dict[int, dict] = {}

    if len(calibrated) < MIN_PEERS_FOR_COMPARISON:
        # Pas assez de points de comparaison : on ne conclut rien.
        for sensor in sensors:
            results[sensor.id] = {
                "status": _status_of(sensor),
                "deviation_percent": None,
                "reference_factor": None,
                "mean_factor": None,
                "peers": len(calibrated),
            }
        return results

    factors = sorted(s.calibration_factor for s in calibrated)
    reference = median(factors)          # robuste aux valeurs aberrantes
    mean_factor = sum(factors) / len(factors)   # informatif seulement

    for sensor in sensors:
        if not sensor.is_calibrated:
            results[sensor.id] = {
                "status": "uncalibrated",
                "deviation_percent": None,
                "reference_factor": round(reference, 6),
                "mean_factor": round(mean_factor, 6),
                "peers": len(calibrated),
            }
            continue
        dev = deviation_percent(sensor.calibration_factor, reference)
        results[sensor.id] = {
            "status": "suspect" if dev > SUSPECT_DEVIATION_PERCENT else "calibrated",
            "deviation_percent": round(dev, 2),
            "reference_factor": round(reference, 6),
            "mean_factor": round(mean_factor, 6),
            "peers": len(calibrated),
        }
    return results


def _status_of(sensor) -> str:
    return "calibrated" if sensor.is_calibrated else "uncalibrated"


def refresh_calibration_status(house) -> dict[str, int]:
    """Recalcule le statut de calibration de tous les capteurs d'une maison.

    Les capteurs sont comparés PAR TYPE (tensions entre elles, courants entre
    eux) : un ZMPT101B et un ZMCT103C n'ont aucune raison d'avoir des
    coefficients du même ordre.
    """
    from .models import Sensor

    counts = {"calibrated": 0, "uncalibrated": 0, "suspect": 0}
    for sensor_type in (Sensor.SensorType.VOLTAGE, Sensor.SensorType.CURRENT):
        group = list(
            Sensor.objects.filter(house=house, sensor_type=sensor_type, is_active=True)
        )
        if not group:
            continue
        verdicts = evaluate_group(group)
        for sensor in group:
            status = verdicts[sensor.id]["status"]
            if sensor.calibration_status != status:
                sensor.calibration_status = status
                sensor.save(update_fields=["calibration_status"])
            counts[status] = counts.get(status, 0) + 1
    return counts

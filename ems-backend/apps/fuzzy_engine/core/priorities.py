"""
Priorité des charges et des lignes — source de vérité unique.

CE QUI ÉTAIT CONTRADICTOIRE

Quatre sources disaient trois choses différentes de la ligne 2 :

  - `actuator.FALLBACK_RANK` : « L2 délestée en premier » ;
  - `esp32/config.h` (clampDecision, repli backend muet) : idem ;
  - `docs/CURRENT_SYSTEM_STATE.md` §2 : « Ligne 2 — Lampe L2 (20 W) seule —
    prioritaire » ;
  - `seed_prototype.py` : la lampe L2 est enregistrée `IMPORTANT`.

ARBITRAGE

Les deux dernières sources l'emportent : ce sont les seules adossées au
matériel réellement monté, et l'écart avait déjà été vérifié physiquement puis
tranché le 19/07/2026 (la lampe 20 W est bien sur la ligne 2). Les deux
premières datent d'avant l'existence du rattachement charge -> ligne
(`Equipment.relay_line`) ; elles codaient en dur une convention que la base
exprime désormais.

Convention retenue, alignée partout :

    ligne 2  = IMPORTANT      -> délestée en DERNIER
    ligne 1  = NORMAL + prise -> délestable
    ligne 3  = NORMAL + prise -> délestable

LE RANG N'EST PAS UNE INTERDICTION

Une seule interdiction absolue existe : une ligne CRITICAL n'est jamais coupée
automatiquement. Tout le reste est un COÛT, pas un veto — c'est ce qui permet à
l'optimiseur d'arbitrer (couper une ligne normale de 20 W plutôt que deux
lignes secondaires de 5 W). Traiter la priorité comme un veto rendait le
délestage inatteignable sur le prototype, puisque aucune de ses lignes n'est
« non prioritaire » au sens strict : chacune porte au moins une lampe normale.
"""
from __future__ import annotations


# Rang de priorité d'une charge : plus haut = plus prioritaire, donc coupé en
# dernier. Les cinq niveaux du modèle Equipment sont couverts ; sans `LOW`, une
# charge « Secondaire » retombait sur le défaut et passait pour normale, alors
# qu'elle doit se délester AVANT une charge normale.
PRIORITY_RANK = {
    "NON_CRITICAL": 0,   # délestée en premier
    "LOW": 1,            # secondaire
    "NORMAL": 2,
    "IMPORTANT": 3,      # prioritaire
    "CRITICAL": 4,       # jamais coupée automatiquement
}

# Rang appliqué à une priorité inconnue : celui de NORMAL, qui est le défaut du
# modèle. Surtout pas 0 — une erreur de saisie ne doit pas rendre une charge
# délestable en premier.
DEFAULT_RANK = PRIORITY_RANK["NORMAL"]

# Priorité d'une ligne à laquelle aucune charge n'est rattachée. La convention
# ci-dessus s'applique : la ligne 2 porte la charge prioritaire du prototype.
FALLBACK_LINE_PRIORITY = {1: "NORMAL", 2: "IMPORTANT", 3: "NORMAL"}

# Regroupement des 5 niveaux en 3 catégories pour la DÉCISION maison : le
# moteur flou n'a besoin que de savoir s'il doit protéger, recommander, ou peut
# délester. Les 5 niveaux restent visibles côté données, interfaces et
# optimiseur ; seul le raisonnement maison les regroupe.
DECISION_CLASS = {
    "CRITICAL": "CRITICAL",
    "IMPORTANT": "PRIORITY",
    "NORMAL": "PRIORITY",
    "LOW": "NON_PRIORITY",
    "NON_CRITICAL": "NON_PRIORITY",
}


def rank(priority: str | None) -> int:
    """Rang numérique d'une priorité, pour comparer et pour coûter."""
    return PRIORITY_RANK.get((priority or "").strip().upper(), DEFAULT_RANK)


def line_priority(priorities) -> str | None:
    """Priorité d'une ligne = celle de la charge la PLUS prioritaire qu'elle porte.

    Jamais une moyenne : couper la ligne coupe TOUT ce qu'elle alimente. Une
    ligne portant une lampe normale et une prise secondaire doit donc être
    traitée comme normale — sinon le moteur croirait ne sacrifier que la prise.
    """
    known = [p for p in priorities if p]
    if not known:
        return None
    return max(known, key=rank)


def is_sheddable(priority: str | None) -> bool:
    """Une ligne peut-elle être coupée automatiquement ?

    Seule une charge CRITIQUE l'interdit. Le reste se paie (cf. l'optimiseur),
    mais reste possible quand la situation le justifie.
    """
    return (priority or "").strip().upper() != "CRITICAL"

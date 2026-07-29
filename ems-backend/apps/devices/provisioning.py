"""
Provisionnement des lignes d'un micro-réseau.

La migration 0013 crée les lignes des micro-réseaux EXISTANTS. Ce module crée
celles des micro-réseaux à venir — sans lui, toute maison créée après la
migration n'aurait aucune ligne, et le raisonnement par ligne du moteur
retomberait silencieusement sur son repli maison.

Le provisionnement est explicite et idempotent : on l'appelle aux deux moments
où un micro-réseau devient pilotable (première lecture de ses relais depuis une
interface, premier sondage d'un nœud), jamais au milieu d'une écriture de
mesures. Créer une entité de topologie en marge d'un enregistrement de
télémétrie rendrait l'origine des lignes impossible à retracer.
"""
from __future__ import annotations

from .models import Line, LineState


# Topologie du prototype (cf. docs/CURRENT_SYSTEM_STATE.md §1 et
# esp32-firmware/.../config.h). Le firmware N'EST PAS modifié par cette
# refonte : ces valeurs le décrivent, elles ne le pilotent pas. Un câblage
# différent se corrige ligne par ligne en base, sans toucher au code.
LIGNES_PAR_DEFAUT = (
    (1, "Ligne 1", 25),
    (2, "Ligne 2", 26),
    (3, "Ligne 3", 27),
)


def ensure_lines(house) -> list[Line]:
    """Crée les trois lignes commutables du micro-réseau si elles manquent.

    Idempotent : rappelée sur un micro-réseau déjà provisionné, elle ne crée
    rien et ne modifie rien — en particulier, elle n'écrase pas un nom ou une
    priorité que l'utilisateur aurait personnalisés.
    """
    if house is None:
        return []

    lignes = []
    for numero, nom, gpio in LIGNES_PAR_DEFAUT:
        ligne, _ = Line.objects.get_or_create(
            house=house,
            number=numero,
            defaults={"name": nom, "relay_gpio": gpio, "is_switchable": True},
        )
        # Toute ligne a un état : sans lui, `LineReading.relay_closed` n'aurait
        # rien à lire et l'optimiseur ignorerait si la ligne est alimentée.
        LineState.objects.get_or_create(line=ligne)
        lignes.append(ligne)
    return lignes

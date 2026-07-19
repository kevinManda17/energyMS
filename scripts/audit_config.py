#!/usr/bin/env python3
"""
Audit de cohérence du projet EMS : adresses codées en dur, valeurs de tension
figées, câblage obsolète dans la doc, confusion d'unités W/kW.

    python scripts/audit_config.py            # rapport lisible
    python scripts/audit_config.py --strict    # code de sortie 1 s'il reste des alertes

Le script signale, il ne corrige pas. Chaque alerte indique le fichier, la ligne
et pourquoi c'est un problème. Certaines occurrences sont légitimes (repli de
développement, exemple de documentation) : elles sont classées en INFO et non
en ALERTE — l'objectif est d'éviter le bruit qui ferait ignorer le rapport.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    "node_modules", ".git", "venv", "venv312", ".venv", "__pycache__",
    "dist", "build", ".pio", "staticfiles", "media", ".expo", "ml_models",
}
SCAN_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".h", ".ino", ".md",
                 ".json", ".yml", ".yaml", ".env", ".example", ".ps1"}

# Adresses LAN utilisées par le passé : ne doivent plus apparaître comme valeur
# active (en commentaire d'historique, c'est acceptable).
OLD_IPS = re.compile(r"\b(?:172\.20\.10\.\d+|192\.168\.(?:203|188)\.\d+)\b")

# Valeurs de tension autrefois forcées. On ne veut plus AUCUN plafonnement.
FORCED_VOLTAGE = re.compile(
    r"(VOLTAGE_DISPLAY_(?:MIN|MAX)|condition_voltage|clamp.{0,20}\b(?:215|224)\b"
    r"|\b(?:215|224)\b\s*(?:<=|>=|,)\s*.{0,20}volt)", re.IGNORECASE)

# Câblage obsolète : la ligne 1 est sur IN2/CH2 (COM2/NO2) depuis le recâblage.
OLD_WIRING = re.compile(r"\b(?:IN1|COM1\s*/?\s*NO1|CH1)\b")

LOCALHOST = re.compile(r"\blocalhost\b|\b127\.0\.0\.1\b")

# Une ligne qui MET EN GARDE contre une valeur obsolète n'est pas une faute :
# la doc doit pouvoir dire « IN1 est obsolète » sans se faire signaler.
WARNING_CONTEXT = re.compile(
    r"obsol[eè]te|obsolete|ne plus|jamais|ancien|autrefois|d[ée]pr[ée]ci|"
    r"historique|au lieu de|plut[oô]t que|remplac|corrig[ée]|retir[ée]",
    re.IGNORECASE)

# Puissance stockée en kW alors que la source est en watts.
UNIT_CONFUSION = re.compile(r'\(\s*["\']consumption["\']\s*,\s*sum\(\s*powers\s*\)')


def iter_files():
    this_file = Path(__file__).resolve()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # Le script contient forcément les motifs qu'il recherche.
        if path.resolve() == this_file:
            continue
        if path.suffix not in SCAN_SUFFIXES and not path.name.startswith(".env"):
            continue
        yield path


def is_comment(line: str, suffix: str) -> bool:
    s = line.strip()
    if suffix in {".py", ".yml", ".yaml", ".ps1"} or s.startswith("#"):
        return s.startswith("#")
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".h", ".ino"}:
        return s.startswith("//") or s.startswith("*") or s.startswith("/*")
    return False


def audit() -> tuple[list[str], list[str]]:
    alerts: list[str] = []
    infos: list[str] = []

    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        is_doc = path.suffix == ".md"
        for n, line in enumerate(lines, 1):
            commented = is_comment(line, path.suffix)
            where = f"{rel}:{n}"
            # Ligne qui documente ce qu'il ne faut PAS faire : on n'alerte pas.
            if WARNING_CONTEXT.search(line):
                continue

            if OLD_IPS.search(line):
                (infos if commented else alerts).append(
                    f"{where} — ancienne IP LAN"
                    + (" (en commentaire, historique)" if commented else
                       " ACTIVE : à remplacer par la config courante"))

            if FORCED_VOLTAGE.search(line) and not commented:
                alerts.append(f"{where} — tension possiblement forcée/plafonnée : "
                              "la calibration doit se faire par coefficient CAL_Vx")

            if OLD_WIRING.search(line) and (is_doc or path.suffix in {".h", ".ino"}):
                alerts.append(f"{where} — câblage obsolète (IN1/CH1/COM1-NO1) : "
                              "la ligne 1 est sur IN2 / CH2 (COM2/NO2)")

            if UNIT_CONFUSION.search(line):
                alerts.append(f"{where} — watts stockés en kW sans division "
                              "par 1000 (confusion W/kW)")

            if LOCALHOST.search(line) and not commented:
                # localhost reste légitime : repli de dev, docker interne, docs.
                infos.append(f"{where} — localhost/127.0.0.1 "
                             "(vérifier que c'est bien un repli de développement)")

    return alerts, infos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="sortie 1 si des alertes subsistent")
    parser.add_argument("--show-info", action="store_true",
                        help="afficher aussi les occurrences tolérées")
    args = parser.parse_args()

    alerts, infos = audit()

    print("=" * 68)
    print("AUDIT DE CONFIGURATION — EMS IoT")
    print("=" * 68)

    if alerts:
        print(f"\nALERTES ({len(alerts)}) — à corriger :\n")
        for item in alerts:
            print(f"  ! {item}")
    else:
        print("\nAucune alerte : pas d'IP obsolète active, pas de tension figée,")
        print("pas de câblage IN1 dans le code/doc, pas de confusion W/kW détectée.")

    print(f"\nINFO ({len(infos)}) — occurrences tolérées "
          f"(localhost de dev, historique en commentaire)")
    if args.show_info:
        for item in infos:
            print(f"  - {item}")
    else:
        print("  (relancer avec --show-info pour les lister)")

    print()
    return 1 if (args.strict and alerts) else 0


if __name__ == "__main__":
    sys.exit(main())

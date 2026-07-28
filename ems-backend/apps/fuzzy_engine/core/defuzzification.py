"""
Alias de compatibilité — le module s'appelle désormais `aggregation`.

L'étape n'a jamais été une défuzzification (cf. l'en-tête de `aggregation.py`).
Ce fichier ne subsiste que pour ne pas casser un import existant ; il sera
retiré une fois les appelants migrés. Rien de neuf ne doit l'importer.
"""
from __future__ import annotations

from .aggregation import SCORE_KEYS, aggregate_rule_results

__all__ = ["SCORE_KEYS", "aggregate_rule_results"]

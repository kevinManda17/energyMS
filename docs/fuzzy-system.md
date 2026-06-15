# Système expert flou

Implémenté dans `apps/fuzzy_engine/engine.py` — règles floues Python structurées
(fonctions d'appartenance triangulaires/trapézoïdales + agrégation par action).

## Variables linguistiques (entrées)

| Variable        | Termes flous                       |
|-----------------|------------------------------------|
| `production_pv` | faible · moyenne · élevée          |
| `consommation`  | faible · modérée · élevée          |
| `batterie_soc`  | déchargée · moyenne · chargée      |
| charges non critiques actives | booléen           |

## Actions possibles (sorties)
`CHARGER_BATTERIE` · `UTILISER_BATTERIE` · `ALIMENTER_CHARGES` ·
`DELESTER_NON_PRIORITAIRES` · `NOTIFIER_UTILISATEUR` · `ATTENDRE`

## Règles
| ID | Condition | Action |
|----|-----------|--------|
| R1 | prod faible ET batterie déchargée ET conso élevée | DELESTER_NON_PRIORITAIRES |
| R2 | prod élevée ET batterie non chargée | CHARGER_BATTERIE |
| R3 | prod moyenne ET conso élevée ET batterie moyenne | UTILISER_BATTERIE |
| R4 | prod élevée ET conso faible | ALIMENTER_CHARGES |
| R5 | prod faible ET conso faible ET batterie moyenne | ATTENDRE |
| R6 | batterie très faible (<15 %) | NOTIFIER_UTILISATEUR |
| R7 | conso élevée ET charges non prioritaires actives | DELESTER_NON_PRIORITAIRES |

## Sortie du moteur
```json
{
  "action": "DELESTER_NON_PRIORITAIRES",
  "reason": "Production faible, batterie déchargée et consommation élevée.",
  "confidence_score": 0.71,
  "input_snapshot": { "production_pv": 0.4, "consommation": 4.0,
                      "batterie_soc": 18, "memberships": { ... } },
  "activated_rules": [ { "id": "R1", "strength": 0.8, ... } ],
  "timestamp": "..."
}
```

`confidence_score` = force de l'action dominante / somme des forces de toutes les
règles activées.

## Exemples de cas
| Production | Conso | SoC | Action attendue |
|-----------|-------|-----|-----------------|
| 0.3 kW    | 5 kW  | 20% | Délester non prioritaires |
| 6 kW      | 1.5 kW| 50% | Charger batterie / Alimenter |
| 2.5 kW    | 4.2 kW| 50% | Utiliser batterie |
| 0.3 kW    | 0.5 kW| 10% | Notifier utilisateur |

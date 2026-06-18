# Systeme expert flou

Le backend utilise maintenant le moteur avance integre dans
`apps/fuzzy_engine/core/`, appele depuis `apps/fuzzy_engine/engine.py`.

## Entrees principales

Le mapper Django construit un `EnergyFacts` a partir des donnees EMS:

| Champ | Source |
|-------|--------|
| `current_pv_power_kw` | Derniere mesure `production` |
| `current_load_power_kw` | Derniere mesure `consumption` |
| `forecast_pv_energy_kwh` | Previsions stockees, sinon fallback prudent |
| `forecast_load_energy_kwh` | Previsions stockees, sinon fallback prudent |
| `battery_soc_percent` | Derniere mesure `battery_soc` |
| `battery_temperature_c` | Derniere mesure `temperature`, sinon 25 C |
| `load_priority` | Equipements actifs, sinon `NON_PRIORITY` |
| `data_quality` | `GOOD`, `PARTIAL` ou `BAD` selon les mesures disponibles |
| `pv_nominal_power_kw` | Capacite PV du micro-reseau, sinon 5.0 |

## Decisions possibles

Le moteur retourne notamment:

- `PROTECT_BATTERY`
- `SHED_NON_PRIORITY_LOAD`
- `RECOMMEND_REDUCE_PRIORITY_LOAD`
- `USE_BATTERY`
- `CHARGE_BATTERY`
- `NORMAL_OPERATION`
- `ECO_MODE`
- `BLOCK_AUTOMATIC_ACTION`
- `DATA_QUALITY_ALERT`

## Sortie API

Les anciens champs restent disponibles pour compatibilite:

- `action`
- `reason`
- `confidence_score`
- `input_snapshot`
- `activated_rules`

Les nouveaux champs exposes par `/api/decisions/` sont:

- `decision_code`, `decision_label`, `execution_mode`, `alert_level`
- `risk_score`, `shedding_level`, `charge_battery_score`
- `discharge_battery_score`, `protect_battery_score`
- `recommendation_score`, `automatic_score`, `blocked_score`
- `battery_action`, `explanation`
- `fired_rules`, `input_facts`, `fuzzy_values`

## Exemple

```json
{
  "decision_code": "SHED_NON_PRIORITY_LOAD",
  "decision_label": "Delester une charge non prioritaire",
  "execution_mode": "AUTOMATIC",
  "alert_level": "CRITICAL",
  "risk_score": 95.0,
  "battery_action": "PRESERVE",
  "confidence_score": 0.95
}
```

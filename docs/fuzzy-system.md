# Systeme expert flou

Le module `apps/fuzzy_engine/` est organise en deux couches (ce ne sont pas des doublons) :

- **`core/`** — le moteur pur (`FuzzyExpertEngine`, `rules.py`, `membership.py`,
  `inference.py`, `defuzzification.py`, `decision_mapper.py`). Logique floue sans
  dependance Django : 24 regles appliquees a un objet `EnergyFacts`.
- **`engine.py`** (a la racine du module) — l'adaptateur Django : `facts_from_house()`
  lit les **dernieres mesures reelles** du micro-reseau en base et construit
  l'`EnergyFacts` qui nourrit le moteur ; `evaluate_house()` l'execute.

Flux : `views.py` (`/decisions/trigger/`) -> `engine.py` (lit la base) -> `core/` (applique les regles).
Aucune decision n'est pre-ecrite : chaque evaluation part de l'etat courant du systeme.

## Entrees principales

`facts_from_house()` construit un `EnergyFacts` a partir des dernieres mesures reelles.
La production/consommation/tension proviennent du noeud ESP32 (via `/ems/decision/`),
l'irradiance/temperature d'Open-Meteo :

| Champ | Source |
| --- | --- |
| `current_pv_power_kw` | Derniere mesure `production` |
| `current_load_power_kw` | Derniere mesure `consumption` |
| `forecast_pv_energy_kwh` | Integration des `Forecast` sur 24 h, sinon `puissance_actuelle x 24 h` |
| `forecast_load_energy_kwh` | Integration des `Forecast` sur 24 h, sinon `puissance_actuelle x 24 h` |
| `battery_soc_percent` | Derniere mesure `battery_soc` |
| `battery_temperature_c` | Derniere mesure **`battery_temp`** (sonde dediee), sinon 25 C. **Jamais** `temperature` (= meteo ambiante) : les regles thermiques batterie n'ont pas a se declencher sur la meteo du jour |
| `load_priority` | Equipements actifs, regroupes en 3 (`CRITICAL` / `PRIORITY` / `NON_PRIORITY`) a partir des 5 niveaux du modele |
| `data_quality` | `GOOD`, `PARTIAL` ou `BAD` selon les mesures disponibles |
| `pv_nominal_power_kw` | Somme des `EnergyAsset` actifs de type `PV_PANEL`, sinon `House.pv_capacity_kw`, sinon 5.0 |

### Faits contextuels enrichis (lot 1)

Additifs, optionnels et **retrocompatibles** : transmis au moteur et traces dans
`Decision.input_facts`, disponibles pour de futures regles sans modifier les 24
regles actuelles. Preserves a travers la normalisation (`dataclasses.replace`).

| Champ | Source | Etat |
| --- | --- | --- |
| `ambient_temperature_c` | Derniere mesure `temperature` (Open-Meteo) | transmis |
| `solar_irradiance_wm2` | Derniere mesure `irradiance` | transmis |
| `module_temperature_c` | Derniere mesure `module_temp` / `panel_temp` | transmis (sonde non posee) |
| `hour` / `day_of_week` | Horloge serveur (0..23 / 0 = lundi) | transmis |
| `operating_mode` | `RelayState.control_mode` (`MANUAL`/`ASSISTED`/`AUTO`) | transmis |

**Lot 2 (perspective)** : puissances predites instantanees, et faits **par charge**
(`load_id`, `nominal_power`, `relay_state`…) — le raisonnement reste **par ligne**
tant qu'il n'y a pas de capteur par charge, et conserve les 5 niveaux de priorite.

## Relations sauvegardees

Une `Decision` peut etre reliee a la derniere `Forecast` disponible pour la maison. Une `Alert` peut etre reliee a la `Decision` qui l'a declenchee.

```text
Forecast -> Decision -> Alert
```

## Decisions possibles

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

Champs principaux :

- `forecast`
- `action`
- `reason`
- `confidence_score`
- `input_snapshot`
- `activated_rules`
- `decision_code`, `decision_label`, `execution_mode`, `alert_level`
- `risk_score`, `shedding_level`, `charge_battery_score`
- `discharge_battery_score`, `protect_battery_score`
- `recommendation_score`, `automatic_score`, `blocked_score`
- `battery_action`, `explanation`
- `fired_rules`, `input_facts`, `fuzzy_values`

## Exemple

```json
{
  "forecast": 12,
  "decision_code": "SHED_NON_PRIORITY_LOAD",
  "decision_label": "Delester une charge non prioritaire",
  "execution_mode": "AUTOMATIC",
  "alert_level": "CRITICAL",
  "risk_score": 95.0,
  "battery_action": "PRESERVE",
  "confidence_score": 0.95
}
```

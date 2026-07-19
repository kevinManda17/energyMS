# Mesures et unités

> Toute modification des unités doit être répercutée ici.
> Vérification : `python scripts/audit_config.py --strict`

Dernière mise à jour : **19/07/2026**

---

## 1. Règle des unités

| Grandeur | Unité | Nature |
|----------|-------|--------|
| Tension | **V** | instantanée |
| Courant | **A** | instantanée |
| Puissance (interne, firmware) | **W** | instantanée |
| Puissance (application) | **kW** | instantanée |
| Énergie consommée | **kWh** | **cumulée sur une durée** |

```
power_w    = voltage_v × current_a × power_factor
power_kw   = power_w / 1000
energy_kwh = Σ (power_kw × Δt_heures)
```

**Ne jamais confondre** : W et kW décrivent une puissance *à un instant* ; Wh et
kWh décrivent une énergie *accumulée dans le temps*. Sommer des puissances sans
multiplier par la durée ne donne pas une énergie.

### Vocabulaire d'interface

| À afficher | Plutôt que |
|------------|------------|
| « Puissance actuelle » (kW) | « Consommation » |
| « Énergie consommée » (kWh) | « Consommation » |

Le terme « consommation » est ambigu : il a été employé pour les deux. Le champ
technique `consumption` reste en base (compatibilité), mais il porte bien une
**puissance en kW**.

---

## 2. Facteur de puissance

`P = U × I × cos(phi)`

Le prototype **ne mesure pas** le déphasage : `POWER_FACTOR = 1.0`.

Conséquence à assumer dans le mémoire : ce qui est calculé est la puissance
**apparente** (VA), assimilée à de la puissance active (W). C'est correct pour
des lampes résistives, optimiste pour un chargeur à découpage. Il s'agit donc
d'une **estimation simplifiée**, pas d'une mesure de puissance active.

---

## 3. Bug historique corrigé (19/07/2026)

Le backend stockait la somme des **watts** de l'ESP32 directement sous l'unité
`kW` : 40 W devenaient « 40 kW », soit un facteur **1000**. Cela faussait le
moteur expert et tous les tableaux de bord.

La conversion est désormais explicite (`WATTS_PER_KILOWATT`) et le backend
enregistre les deux :

| Type de mesure | Unité | Contenu |
|----------------|-------|---------|
| `power` | W | puissance totale brute |
| `consumption` | kW | la même, divisée par 1000 |

> ⚠ **Les mesures enregistrées avant cette correction restent fausses d'un
> facteur 1000.** Elles n'ont pas été rétro-corrigées : impossible de distinguer
> après coup les valeurs déjà justes. En tenir compte pour toute analyse
> d'historique.

---

## 4. Structure d'une mesure

Chaque mesure est rattachée au capteur qui l'a produite.

| Champ | Rôle |
|-------|------|
| `sensor` | capteur émetteur (donne code, type, ligne) |
| `measurement_type` | nature de la grandeur |
| `value` | valeur **physique** (calibrée) dans `unit` |
| `raw_value` | valeur **brute** du capteur (RMS, volts ADC) |
| `calibration_factor_used` | coefficient appliqué à cet instant |
| `calibration_offset_used` | offset appliqué à cet instant |
| `quality_status` | qualité/anomalie éventuelle |
| `timestamp` | horodatage de la mesure |

Conserver `raw_value` et les coefficients utilisés permet de **recalculer** un
historique après une recalibration, sans le fausser rétroactivement.

Exemple tension :

```json
{"sensor_code": "V1", "sensor_type": "voltage", "line_number": 1,
 "raw_value": 1.84, "value": 218.7, "unit": "V"}
```

Exemple courant :

```json
{"sensor_code": "I1", "sensor_type": "current", "line_number": 1,
 "raw_value": 0.086, "value": 0.045, "unit": "A"}
```

Puissance de ligne — **calculée**, pas mesurée :

```json
{"line_number": 1, "voltage_sensor": "V1", "current_sensor": "I1",
 "voltage_v": 218.7, "current_a": 0.045, "power_kw": 0.0098}
```

---

## 5. Températures — types distincts

| Type | Source | Usage |
|------|--------|-------|
| `temperature` | API météo (Open-Meteo) | température **ambiante** |
| `battery_temp` | sonde dédiée — **non installée** | température batterie |
| `panel_temp` | sonde dédiée — **non installée** | température panneau |
| `module_temp` | jeu de données PV | modèle de prévision |

Le système expert lit **`battery_temp` uniquement**. Sans sonde, il retient
25 °C (valeur neutre) : les règles thermiques batterie restent inactives, ce qui
est voulu. Auparavant il lisait la météo comme température de batterie.

---

## 6. Pagination et filtres

`GET /api/measurements/`

| Paramètre | Effet |
|-----------|-------|
| `page`, `page_size` | pagination (défaut 50, max 500) |
| `sensor_code` | filtre par code : `V1`, `I2`… |
| `sensor_type` | `voltage`, `current` |
| `line_number` | 1, 2 ou 3 |
| `measurement_type` | type de grandeur |
| `house`, `sensor` | par identifiant |
| `start`, `end` | bornes temporelles (ISO 8601) |
| `ordering` | `-timestamp` par défaut (plus récent d'abord) |

Les séries grossissent vite (un relevé toutes les 30 s) : **ne jamais charger
tout**. Le mobile demande de petites pages, le web des pages plus larges.

---

## 7. Limites actuelles

- **Capteurs non calibrés** : les valeurs affichées ne sont pas encore des
  volts/ampères réels (voir `SENSORS_AND_CALIBRATION.md`).
- **Facteur de puissance non mesuré** : puissance apparente assimilée à active.
- **Énergie (kWh)** : l'intégration temporelle existe côté prévision
  (`_prediction_energy`, pondération par Δt) mais il n'y a pas encore de
  compteur d'énergie cumulée persistant par ligne.
- **Historique antérieur au 19/07/2026** : consommations fausses ×1000.

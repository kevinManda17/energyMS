# Analyse de conformite - architecture cible EMS

Date : 2026-06-23

## 1. Fichiers analyses

Cette analyse se base uniquement sur les trois fichiers demandes :

- `docs/EMS_cahier_des_charges_MoSCoW.docx`
- `docs/EMS_modifications_systeme_codex.md`
- `docs/EMS_architecture_MCD_MLD_MPD_diagrammes.md`

Ces fichiers doivent devenir la reference cible du systeme EMS.

## 2. Orientation cible confirmee

Le systeme doit etre recentre sur la chaine suivante :

```text
collecte IoT
-> mesures
-> modeles pre-entraines importes
-> prevision
-> decision floue
-> alerte
-> supervision web/mobile
```

Point important : le backend ne doit pas etre presente comme une plateforme
d'entrainement Machine Learning. L'entrainement des modeles est hors backend :
il se fait dans des notebooks ou scripts externes. Le backend sert a importer
des modeles deja entraines, executer l'inference, stocker les previsions et
alimenter le systeme expert flou.

## 3. Modele cible du domaine

Le domaine cible se structure autour des entites suivantes :

| Entite | Role cible |
| --- | --- |
| `User` | Compte utilisateur, role, securite, preferences. |
| `House` | Site logique ou micro-reseau domestique. |
| `EnergyAsset` | Actif energetique physique : panneau PV, batterie, onduleur, regulateur, reseau, generateur. |
| `Sensor` | Capteur rattache a une maison et optionnellement a un actif energetique. |
| `Equipment` | Charge consommatrice ou delestable, avec priorite. |
| `Measurement` | Valeur IoT mesuree. |
| `ImportedModel` | Modele de prevision pre-entraine importe dans le backend. |
| `Forecast` | Resultat d'une prevision production ou consommation. |
| `Decision` | Decision energetique issue du systeme expert flou. |
| `Alert` | Alerte generee par une decision ou un etat anormal. |
| `DataExport` | Export de donnees collectees pour analyse ou reentrainement externe. |

Relation metier centrale :

```text
House
  -> EnergyAsset
      -> Sensor
          -> Measurement
  -> Equipment
  -> Forecast
      -> Decision
          -> Alert
```

## 4. Conformite du code actuel

| Domaine | Etat actuel observe | Conformite |
| --- | --- | --- |
| Utilisateurs | `User` existe avec role, email unique, telephone, preferences. Changement de mot de passe present. | Partiel |
| Verification email / reset password | Le code contient surtout verification telephone et changement de mot de passe. Les tokens email/reset ne sont pas encore modelises. | Non conforme |
| House | `House` existe, mais contient encore `pv_capacity_kw` et `battery_capacity_kwh`. | Partiel |
| EnergyAsset | L'application `energy_assets` n'existe pas encore. | Non conforme |
| Sensor | `Sensor` existe, mais il n'a pas encore de lien `energy_asset`. | Partiel |
| Equipment | `Equipment` existe avec priorites `CRITICAL`, `IMPORTANT`, `NORMAL`, `NON_CRITICAL`. | Conforme |
| Measurement | `Measurement` existe, reliee a `House` et `Sensor`, avec index house/type/timestamp. | Majoritairement conforme |
| Types de mesures | Production, consumption, battery_soc, voltage, current, power, temperature existent. `luminosity` et `irradiance` manquent. | Partiel |
| Datasets | `datasets` existe encore comme module d'import CSV/JSON admin. La cible demande de le deplacer vers export ou reports. | Non conforme |
| Reports / exports | Export CSV de mesures existe dans `reports`, mais pas de modele `DataExport` ni d'historique d'exports. | Partiel |
| Forecasting | Le code utilise `ForecastModel` et `Prediction`, avec `HourlyProfileForecast`. Il existe encore un endpoint `forecasting/train/`. | Partiel / a corriger |
| ImportedModel / Forecast | Les entites cible `ImportedModel` et `Forecast` n'existent pas sous cette forme. | Non conforme |
| Fuzzy engine | `Decision` est riche et explicable, mais pas encore reliee a une prevision par `forecast_id`. | Partiel |
| Alert | `Alert` existe, mais sans lien direct `decision_id`. | Partiel |
| MQTT | MQTT existe via `mqtt_handler`. | Partiel |
| Edge Gateway | Edge gateway existe, cache et synchronise les mesures. Le payload ne transmet pas encore `sensor_id` et `energy_asset_id`. | Partiel |
| Front web | Il faut ajouter/adapter actifs energetiques, import modele, export donnees, email/reset. | A verifier/adapter |
| Mobile | Il faut ajouter API cloud/local edge, actifs energetiques, derniere prevision, derniere decision, alertes critiques, changement mot de passe. | A verifier/adapter |

## 5. Ecarts majeurs a corriger

### 5.1 Ajouter `energy_assets`

L'ecart le plus important est l'absence de l'application `energy_assets`.
Elle est obligatoire dans les trois documents de reference.

Actions attendues :

- creer `apps/energy_assets` ;
- creer le modele `EnergyAsset` ;
- ajouter serializers, views, urls, admin ;
- ajouter les endpoints CRUD ;
- limiter l'acces aux actifs des maisons de l'utilisateur ;
- permettre a l'admin de tout voir.

Types attendus :

```text
PV_PANEL
BATTERY
INVERTER
SOLAR_CONTROLLER
GRID_SOURCE
GENERATOR
```

### 5.2 Nettoyer `House`

`House` doit representer le micro-reseau comme site logique. Elle ne doit pas
porter directement les caracteristiques PV/batterie.

Actions attendues :

- migrer `pv_capacity_kw` vers un `EnergyAsset` de type `PV_PANEL` ;
- migrer `battery_capacity_kwh` vers un `EnergyAsset` de type `BATTERY` ;
- retirer ensuite ces champs de `House` ;
- adapter serializers, seed, frontend web et mobile.

### 5.3 Relier `Sensor` a `EnergyAsset`

La cible documentaire impose :

```text
EnergyAsset -> Sensor -> Measurement
```

Action attendue :

```python
energy_asset = models.ForeignKey(
    "energy_assets.EnergyAsset",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="sensors",
)
```

### 5.4 Revoir `forecasting`

La cible veut un module d'inference, pas un module d'entrainement.

Actions attendues :

- remplacer ou faire evoluer `ForecastModel` vers `ImportedModel` ;
- remplacer ou faire evoluer `Prediction` vers `Forecast` ;
- garder `HourlyProfileForecast` comme fallback ;
- retirer ou renommer l'endpoint `forecasting/train/` ;
- ajouter l'import de modele pre-entraine ;
- enregistrer les entrees utilisees dans `input_snapshot` ;
- relier les previsions au systeme expert flou.

Endpoints cible :

```text
POST /api/forecasting/models/import/
GET  /api/forecasting/models/
POST /api/forecasting/predict/
GET  /api/forecasting/forecasts/
GET  /api/forecasting/forecasts/latest/
```

### 5.5 Transformer `datasets`

Le module `datasets` ne doit plus etre visible comme centre de la logique
metier. Les donnees servent a l'export ou au reentrainement externe.

Option recommandee :

- remplacer conceptuellement `datasets` par `data_exports`.

Option simple :

- garder l'export dans `reports` ;
- ajouter un modele `DataExport` pour historiser les exports ;
- supprimer toute presentation du backend comme outil d'entrainement.

### 5.6 Relier `Decision` et `Alert`

La cible prevoit :

```text
Forecast -> Decision -> Alert
```

Actions attendues :

- ajouter `forecast_id` nullable dans `Decision` ;
- ajouter `decision_id` nullable dans `Alert` ;
- utiliser ces relations dans les serializers et vues ;
- creer une alerte automatiquement quand `alert_level` est critique ou warning.

### 5.7 Completer l'authentification

Le cahier des charges attend :

- verification email ;
- demande de reset password ;
- confirmation de reset password ;
- changement de mot de passe connecte ;
- configuration email par variables d'environnement.

Le changement de mot de passe existe deja, mais email verification et reset
password doivent etre ajoutes.

### 5.8 Adapter Edge Gateway et MQTT

Le payload cible doit contenir :

```json
{
  "house_id": 1,
  "sensor_id": 3,
  "energy_asset_id": 1,
  "type": "production",
  "value": 0.42,
  "unit": "kW",
  "timestamp": "2026-06-23T12:30:00Z"
}
```

Actions attendues :

- accepter `sensor_id` dans l'API measurements ;
- conserver le lien indirect vers `EnergyAsset` via `Sensor` ;
- permettre a l'edge de synchroniser `sensor_id` ;
- ne pas rendre `energy_asset_id` obligatoire dans `Measurement` si le lien
  `Sensor -> EnergyAsset` suffit.

## 6. Priorite de correction conseillee

### Priorite 1 - Socle modele de donnees

1. Creer `energy_assets`.
2. Migrer les champs energie de `House` vers `EnergyAsset`.
3. Ajouter `Sensor.energy_asset`.
4. Adapter `Measurement`, MQTT et Edge Gateway.

### Priorite 2 - Prevision et decision

1. Creer `ImportedModel`.
2. Creer/renommer `Forecast`.
3. Garder `HourlyProfileForecast` comme fallback.
4. Supprimer la logique apparente d'entrainement backend.
5. Relier `Forecast -> Decision -> Alert`.

### Priorite 3 - Export et authentification

1. Transformer `datasets` en export ou l'integrer a `reports`.
2. Ajouter `DataExport`.
3. Ajouter verification email.
4. Ajouter reset password.

### Priorite 4 - Interfaces web/mobile

1. Ajouter la gestion des actifs energetiques.
2. Ajouter l'import de modele pre-entraine.
3. Ajouter les exports de donnees.
4. Ajouter les vues email/reset password.
5. Ajouter cote mobile le choix API cloud/local edge.

## 7. Elements a ne pas faire

Les trois documents sont clairs sur ces points :

- ne pas transformer le backend en plateforme d'entrainement ML ;
- ne pas laisser `House` porter les caracteristiques des panneaux ou batteries ;
- ne pas supprimer `Equipment` ;
- ne pas faire de `datasets` le coeur du systeme ;
- ne pas imposer une API meteo pour que le systeme fonctionne ;
- ne pas integrer maintenant un agent conversationnel complet ;
- ne pas presenter la prevision actuelle comme un Random Forest si le code
  execute seulement un fallback de profil horaire.

## 8. Conclusion

Les trois documents sont coherents entre eux et definissent une cible plus
propre que l'etat actuel du code. Le projet actuel possede deja une bonne base
pour `users`, `houses`, `devices`, `measurements`, `reports`, `alerts`,
`mqtt_handler`, `edge-gateway` et `fuzzy_engine`, mais il doit encore etre
restructure autour de `EnergyAsset`, `ImportedModel`, `Forecast` et `DataExport`.

La correction la plus importante est donc de separer clairement :

```text
House = micro-reseau logique
EnergyAsset = composant energetique physique
Sensor = point de mesure
Measurement = valeur mesuree
ImportedModel = modele pre-entraine
Forecast = resultat d'inference
Decision = decision floue explicable
Alert = notification issue de la decision ou d'un etat anormal
```


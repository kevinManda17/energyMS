# EMS - Modifications à apporter au système actuel

Document destiné à être donné à Codex pour mettre à jour le projet `energyMS` selon l'orientation retenue.

## 1. Objectif de la mise à jour

Le système actuel doit être recentré sur la chaîne réelle suivante :

```text
collecte IoT -> mesures -> modèles pré-entraînés importés -> prévision -> décision floue -> alerte -> supervision
```

Le backend ne doit pas être présenté comme une plateforme d'entraînement de datasets. Les modèles sont entraînés séparément dans des notebooks ou scripts spécialisés, puis importés dans le backend pour effectuer l'inférence sur de nouvelles données collectées.

## 2. Modifications fonctionnelles majeures

### 2.1 Ajouter une application backend `energy_assets`

Créer une nouvelle application Django :

```bash
python manage.py startapp energy_assets apps/energy_assets
```

Puis l'ajouter dans `INSTALLED_APPS` :

```python
'apps.energy_assets',
```

Rôle du module : représenter les composants énergétiques principaux d'une maison ou micro-réseau domestique.

Types d'actifs énergétiques attendus :

```text
PV_PANEL
BATTERY
INVERTER
SOLAR_CONTROLLER
GRID_SOURCE
GENERATOR
```

Statuts attendus :

```text
ACTIVE
INACTIVE
FAULT
MAINTENANCE
```

Modèle proposé :

```python
# apps/energy_assets/models.py
from django.db import models


class EnergyAsset(models.Model):
    class AssetType(models.TextChoices):
        PV_PANEL = 'PV_PANEL', 'Panneau photovoltaïque'
        BATTERY = 'BATTERY', 'Batterie'
        INVERTER = 'INVERTER', 'Onduleur'
        SOLAR_CONTROLLER = 'SOLAR_CONTROLLER', 'Régulateur solaire'
        GRID_SOURCE = 'GRID_SOURCE', 'Source réseau'
        GENERATOR = 'GENERATOR', 'Générateur'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        INACTIVE = 'INACTIVE', 'Inactif'
        FAULT = 'FAULT', 'Défaillant'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    house = models.ForeignKey(
        'houses.House',
        on_delete=models.CASCADE,
        related_name='energy_assets'
    )
    name = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=30, choices=AssetType.choices)
    nominal_power_kw = models.FloatField(null=True, blank=True)
    capacity_kwh = models.FloatField(null=True, blank=True)
    voltage = models.FloatField(null=True, blank=True)
    current = models.FloatField(null=True, blank=True)
    efficiency = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.asset_type})'
```

Créer aussi :

```text
apps/energy_assets/serializers.py
apps/energy_assets/views.py
apps/energy_assets/urls.py
apps/energy_assets/admin.py
```

Endpoints attendus :

```text
GET    /api/energy-assets/
POST   /api/energy-assets/
GET    /api/energy-assets/{id}/
PUT    /api/energy-assets/{id}/
PATCH  /api/energy-assets/{id}/
DELETE /api/energy-assets/{id}/
GET    /api/houses/{house_id}/energy-assets/
```

Contraintes :

```text
- Un utilisateur ne peut accéder qu'aux EnergyAsset de ses propres maisons.
- Un admin peut tout voir.
- Les champs numériques doivent accepter null lorsqu'ils ne s'appliquent pas au type d'actif.
- Le champ metadata sert aux propriétés spécifiques : orientation, inclinaison, type panneau, modèle batterie, etc.
```

### 2.2 Nettoyer le modèle `House`

Le modèle `House` doit représenter le site ou micro-réseau, pas les composants énergétiques.

Retirer ou déprécier les champs énergétiques directs s'ils existent :

```text
pv_capacity_kw
battery_capacity_kwh
inverter_power_kw
battery_voltage
panel_type
```

Garder dans `House` seulement :

```text
owner
name
location
latitude
longitude
description
status
created_at
updated_at
```

Si les champs existent déjà en base, créer une migration progressive :

1. Ajouter `EnergyAsset`.
2. Créer une migration de données qui transforme `pv_capacity_kw` et `battery_capacity_kwh` en lignes `EnergyAsset`.
3. Supprimer ensuite les anciens champs de `House`.

Exemple de migration de données attendue :

```python
# créer PV_PANEL si house.pv_capacity_kw existe
# créer BATTERY si house.battery_capacity_kwh existe
```

### 2.3 Adapter `Sensor` pour relier les capteurs aux actifs énergétiques

Dans `apps/devices/models.py`, modifier `Sensor` pour permettre l'association optionnelle à un `EnergyAsset`.

```python
energy_asset = models.ForeignKey(
    'energy_assets.EnergyAsset',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='sensors'
)
```

Logique attendue :

```text
EnergyAsset -> Sensor -> Measurement
```

Exemples :

```text
Panneau PV -> capteur production -> mesures de production
Batterie -> capteur SoC -> mesures battery_soc
Onduleur -> capteur sortie AC -> mesures voltage/current/power
```

### 2.4 Maintenir `Equipment` dans `devices`

Ne pas supprimer `Equipment`.

Rôle : représenter les charges consommatrices ou délestables.

Exemples :

```text
lampe
frigo
routeur
pompe
ventilateur
télévision
```

Le système expert flou doit pouvoir utiliser la priorité des équipements :

```text
CRITICAL
IMPORTANT
NORMAL
NON_CRITICAL
```

### 2.5 Maintenir `Measurement` comme entité centrale

`Measurement` reste indispensable. Elle doit stocker les valeurs issues des capteurs ou de l'edge gateway.

Types recommandés :

```text
production
consumption
battery_soc
voltage
current
power
temperature
luminosity
irradiance
```

Adapter le serializer et les filtres pour accepter :

```text
house
sensor
measurement_type
start_date
end_date
latest
```

Index recommandés :

```python
models.Index(fields=['house', 'measurement_type', '-timestamp'])
models.Index(fields=['sensor', '-timestamp'])
```

### 2.6 Transformer `datasets` en export de données ou le fusionner dans `reports`

Le module `datasets` ne doit plus être au centre du système.

Deux options sont possibles :

#### Option recommandée : renommer conceptuellement en `data_exports`

Rôle : exporter les données collectées afin de produire des fichiers réutilisables pour un réentraînement externe.

Modèle proposé :

```python
class DataExport(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    house = models.ForeignKey('houses.House', on_delete=models.CASCADE)
    export_type = models.CharField(max_length=30)  # measurements, forecasts, decisions, full
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    file_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Option simple : intégrer l'export dans `reports`

Conserver `reports` comme module responsable de :

```text
- rapports journaliers ;
- export CSV des mesures ;
- export CSV des prévisions ;
- export CSV des décisions ;
- export dataset complet pour entraînement externe.
```

Dans tous les cas, ne pas dire dans le code ou les docs que le backend entraîne automatiquement les modèles à partir de datasets.

### 2.7 Revoir `forecasting` comme module d'inférence avec modèles importés

La partie forecasting doit :

```text
1. charger un modèle déjà entraîné ;
2. préparer les entrées à partir des mesures récentes, des actifs énergétiques et éventuellement de la météo ;
3. exécuter le modèle ;
4. enregistrer la prévision ;
5. transmettre la prévision au système expert flou.
```

Créer ou adapter le modèle `ImportedModel` :

```python
class ImportedModel(models.Model):
    class Target(models.TextChoices):
        PRODUCTION = 'production', 'Production'
        CONSUMPTION = 'consumption', 'Consommation'

    name = models.CharField(max_length=120)
    target = models.CharField(max_length=20, choices=Target.choices)
    model_type = models.CharField(max_length=50)  # random_forest, gradient_boosting, lstm, gru, profile
    file = models.FileField(upload_to='models/')
    version = models.CharField(max_length=50, default='v1')
    input_schema = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    imported_at = models.DateTimeField(auto_now_add=True)
```

Créer ou adapter le modèle `Forecast` :

```python
class Forecast(models.Model):
    house = models.ForeignKey('houses.House', on_delete=models.CASCADE, related_name='forecasts')
    model = models.ForeignKey('forecasting.ImportedModel', on_delete=models.SET_NULL, null=True)
    target = models.CharField(max_length=20)
    forecast_value = models.FloatField()
    horizon_minutes = models.PositiveIntegerField(default=60)
    input_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Endpoints attendus :

```text
POST /api/forecasting/models/import/
GET  /api/forecasting/models/
POST /api/forecasting/predict/
GET  /api/forecasting/forecasts/
GET  /api/forecasting/forecasts/latest/
```

Le service doit accepter deux modes :

```text
MODE_PROFILE : prévision simple basée sur profils horaires et mesures récentes.
MODE_IMPORTED_MODEL : prévision avec modèle importé via joblib ou autre format compatible.
```

Pour l'intégration météo, prévoir seulement une interface extensible :

```text
WeatherProviderInterface
- get_current_weather(location)
- get_solar_features(location, timestamp)
```

Ne pas rendre l'API météo obligatoire pour que le système fonctionne.

### 2.8 Système expert flou : utiliser les prévisions et l'état énergétique réel

Le module `fuzzy_engine` doit utiliser :

```text
production prévue
consommation prévue
battery_soc
priorité des équipements
état des actifs énergétiques
mesures récentes
```

La décision doit enregistrer :

```text
action
reason
confidence_score
input_snapshot
activated_rules
alert_level
risk_score
created_at
```

Actions possibles :

```text
CHARGE_BATTERY
USE_BATTERY
SUPPLY_LOADS
SHED_NON_CRITICAL_LOADS
NOTIFY_USER
WAIT
```

### 2.9 Ajouter l'authentification par mail et le changement/réinitialisation de mot de passe

Ajouter les fonctionnalités suivantes :

```text
- vérification d'adresse e-mail ;
- demande de réinitialisation du mot de passe ;
- confirmation de réinitialisation avec token ;
- changement de mot de passe pour utilisateur connecté ;
- envoi d'e-mail configurable par variables d'environnement.
```

Endpoints attendus :

```text
POST /api/auth/email/verify/request/
POST /api/auth/email/verify/confirm/
POST /api/auth/password/reset/request/
POST /api/auth/password/reset/confirm/
POST /api/auth/password/change/
```

Modèles possibles :

```python
class EmailVerificationToken(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PasswordResetToken(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Variables d'environnement à ajouter :

```text
EMAIL_BACKEND=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=
FRONTEND_URL=http://localhost:5173
PASSWORD_RESET_TOKEN_MINUTES=30
EMAIL_VERIFICATION_TOKEN_MINUTES=60
```

### 2.10 Frontend React à adapter

Ajouter ou ajuster les écrans suivants :

```text
- gestion des actifs énergétiques ;
- import des modèles de prévision ;
- lancement d'une prévision ;
- export des données collectées ;
- demande de réinitialisation du mot de passe ;
- confirmation de réinitialisation ;
- changement de mot de passe dans paramètres ;
- vérification e-mail.
```

### 2.11 Mobile React Native à adapter

Ajouter dans les paramètres mobiles :

```text
- choix API cloud / API locale edge ;
- statut de connexion API ;
- affichage des actifs énergétiques principaux ;
- dernière prévision ;
- dernière décision ;
- alertes critiques ;
- changement de mot de passe.
```

### 2.12 Edge Gateway à adapter

L'edge gateway doit pouvoir publier ou synchroniser des mesures associées à :

```text
house_id
sensor_id
energy_asset_id optionnel
measurement_type
value
unit
timestamp
```

Payload MQTT recommandé :

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

## 3. Tests à écrire ou mettre à jour

### 3.1 Backend

Créer ou compléter :

```text
ems-backend/tests/test_energy_assets.py
ems-backend/tests/test_auth_email_password.py
ems-backend/tests/test_forecasting_imported_models.py
ems-backend/tests/test_data_exports.py
ems-backend/tests/test_measurements_energy_asset_link.py
ems-backend/tests/test_fuzzy_engine_with_forecast.py
```

Tests EnergyAsset :

```text
- création d'un PV_PANEL ;
- création d'une BATTERY ;
- association à une House ;
- un utilisateur ne voit pas les actifs d'une maison qui ne lui appartient pas ;
- suppression d'une House supprime ses actifs ;
- validation des choix asset_type/status.
```

Tests Sensor/Measurement :

```text
- créer un Sensor lié à un EnergyAsset ;
- créer une Measurement liée au Sensor ;
- filtrer les mesures par house, type et période ;
- récupérer latest measurements ;
- vérifier les index et l'ordre décroissant timestamp.
```

Tests Forecasting :

```text
- importer un modèle factice ;
- lancer une prédiction production ;
- lancer une prédiction consommation ;
- enregistrer un Forecast ;
- fallback en mode profil horaire si aucun modèle importé actif ;
- erreur propre si input_schema incompatible.
```

Tests Fuzzy Engine :

```text
- décision de charge batterie si production élevée et batterie faible ;
- délestage si production faible, consommation élevée et batterie critique ;
- création d'une alerte si alert_level critique ;
- input_snapshot contient forecast + battery_soc + équipements prioritaires.
```

Tests Auth mail/password :

```text
- demander vérification mail ;
- confirmer vérification mail ;
- refuser token expiré ;
- demander reset password ;
- confirmer reset password ;
- refuser token déjà utilisé ;
- changer mot de passe utilisateur connecté ;
- ancien mot de passe invalide refusé.
```

Tests DataExport :

```text
- exporter mesures CSV ;
- exporter prévisions CSV ;
- exporter décisions CSV ;
- filtrer par période ;
- interdire export d'une maison non possédée.
```

### 3.2 Frontend

Créer ou compléter :

```text
src/test/EnergyAssets.test.jsx
src/test/PasswordReset.test.jsx
src/test/ForecastingImport.test.jsx
src/test/DataExport.test.jsx
```

### 3.3 Mobile

Créer ou compléter :

```text
__tests__/apiMode.test.js
__tests__/passwordChange.test.js
__tests__/energyAssets.test.js
```

## 4. Documentation à mettre à jour

Mettre à jour :

```text
README.md
docs/architecture.md
docs/api-endpoints.md
docs/deployment.md
docs/environment-variables.md
docs/fuzzy-system.md
```

Ajouter :

```text
docs/energy-assets.md
docs/forecasting-imported-models.md
docs/data-export.md
docs/auth-email-password.md
docs/diagrams/
```

## 5. Critères d'acceptation

La mise à jour est acceptée si :

```text
- EnergyAsset existe et est relié à House ;
- House ne contient plus les champs énergétiques détaillés ;
- Sensor peut être relié à EnergyAsset ;
- Measurement reste la source des données mesurées ;
- Forecasting utilise des modèles importés ou un fallback profil horaire ;
- datasets n'est plus présenté comme module central d'entraînement ;
- les exports de données existent ;
- l'authentification par e-mail et le reset password existent ;
- les tests backend critiques passent ;
- la documentation est mise à jour ;
- Docker continue de lancer le projet en local.
```

## 6. Commandes attendues après modification

```bash
cd ems-backend
python manage.py makemigrations
python manage.py migrate
pytest

cd ../ems-frontend
npm test
npm run build

cd ../ems-mobile
npm test

cd ..
docker compose up --build
```

## 7. Ce qu'il ne faut pas faire

```text
- Ne pas développer l'agent conversationnel maintenant.
- Ne pas transformer le backend en plateforme d'entraînement ML complète.
- Ne pas supprimer Measurement.
- Ne pas supprimer Equipment.
- Ne pas mélanger les caractéristiques PV/batterie dans House.
- Ne pas rendre l'API météo obligatoire.
- Ne pas casser les endpoints existants sans prévoir une migration ou une compatibilité.
```

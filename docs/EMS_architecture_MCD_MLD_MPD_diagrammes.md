# EMS - Architecture, MCD, MLD, MPD et scripts de génération des diagrammes

Ce document rassemble les modèles de données et les scripts permettant de générer les diagrammes nécessaires au mémoire.

## 1. Architecture métier retenue

La structure conceptuelle retenue est :

```text
House / Micro-réseau
  -> EnergyAsset : éléments qui produisent, stockent ou convertissent l'énergie
  -> Sensor : éléments qui mesurent
  -> Equipment : charges consommant l'énergie
  -> Measurement : valeurs mesurées
  -> Forecast : prévisions de production ou de consommation
  -> Decision : décisions issues du système expert flou
  -> Alert : alertes produites par le système
```

Règle de séparation :

```text
House = site logique ou micro-réseau
EnergyAsset = actifs énergétiques physiques
Sensor = capteurs
Equipment = charges consommables ou délestables
Measurement = valeurs mesurées
Forecast = valeurs prédites
Decision = action énergétique recommandée
Alert = notification ou incident
```

## 2. MCD - Modèle conceptuel de données

```mermaid

erDiagram
    USER ||--o{ HOUSE : possede
    HOUSE ||--o{ ENERGY_ASSET : contient
    HOUSE ||--o{ SENSOR : possede
    HOUSE ||--o{ EQUIPMENT : possede
    HOUSE ||--o{ MEASUREMENT : recoit
    HOUSE ||--o{ FORECAST : genere
    HOUSE ||--o{ DECISION : produit
    HOUSE ||--o{ ALERT : declenche
    USER ||--o{ DATA_EXPORT : demande

    ENERGY_ASSET ||--o{ SENSOR : est_mesure_par
    SENSOR ||--o{ MEASUREMENT : produit
    IMPORTED_MODEL ||--o{ FORECAST : execute
    FORECAST ||--o{ DECISION : alimente
    DECISION ||--o{ ALERT : peut_generer

    USER {
        int id PK
        string username
        string email
        string role
        string phone
    }

    HOUSE {
        int id PK
        int owner_id FK
        string name
        string location
        string status
    }

    ENERGY_ASSET {
        int id PK
        int house_id FK
        string name
        string asset_type
        float nominal_power_kw
        float capacity_kwh
        float voltage
        float current
        float efficiency
        string status
        json metadata
    }

    SENSOR {
        int id PK
        int house_id FK
        int energy_asset_id FK
        string name
        string sensor_type
        string unit
        bool is_active
    }

    EQUIPMENT {
        int id PK
        int house_id FK
        string name
        string equipment_type
        float rated_power_kw
        string priority
        string status
    }

    MEASUREMENT {
        int id PK
        int house_id FK
        int sensor_id FK
        string measurement_type
        float value
        string unit
        datetime timestamp
    }

    IMPORTED_MODEL {
        int id PK
        string name
        string target
        string model_type
        string file_path
        string version
        json input_schema
        json metrics
        bool is_active
    }

    FORECAST {
        int id PK
        int house_id FK
        int model_id FK
        string target
        float forecast_value
        int horizon_minutes
        json input_snapshot
        datetime created_at
    }

    DECISION {
        int id PK
        int house_id FK
        int forecast_id FK
        string action
        string reason
        float confidence_score
        json input_snapshot
        json activated_rules
        string alert_level
        float risk_score
        datetime created_at
    }

    ALERT {
        int id PK
        int house_id FK
        int decision_id FK
        string severity
        string alert_type
        string message
        bool is_read
        datetime created_at
    }

    DATA_EXPORT {
        int id PK
        int user_id FK
        int house_id FK
        string export_type
        datetime start_date
        datetime end_date
        string file_path
        datetime created_at
    }
```

## 3. MLD - Modèle logique de données

```text
USER(
  id PK,
  username,
  email UNIQUE,
  password,
  role,
  phone,
  phone_verified,
  preferences,
  created_at
)

EMAIL_VERIFICATION_TOKEN(
  id PK,
  user_id FK -> USER(id),
  token_hash,
  expires_at,
  used_at,
  created_at
)

PASSWORD_RESET_TOKEN(
  id PK,
  user_id FK -> USER(id),
  token_hash,
  expires_at,
  used_at,
  created_at
)

HOUSE(
  id PK,
  owner_id FK -> USER(id),
  name,
  location,
  latitude,
  longitude,
  description,
  status,
  created_at,
  updated_at
)

ENERGY_ASSET(
  id PK,
  house_id FK -> HOUSE(id),
  name,
  asset_type,
  nominal_power_kw,
  capacity_kwh,
  voltage,
  current,
  efficiency,
  status,
  metadata,
  created_at,
  updated_at
)

SENSOR(
  id PK,
  house_id FK -> HOUSE(id),
  energy_asset_id FK -> ENERGY_ASSET(id) NULL,
  name,
  sensor_type,
  unit,
  is_active,
  created_at
)

EQUIPMENT(
  id PK,
  house_id FK -> HOUSE(id),
  name,
  equipment_type,
  rated_power_kw,
  priority,
  status,
  created_at
)

MEASUREMENT(
  id PK,
  house_id FK -> HOUSE(id),
  sensor_id FK -> SENSOR(id) NULL,
  measurement_type,
  value,
  unit,
  timestamp,
  created_at
)

IMPORTED_MODEL(
  id PK,
  name,
  target,
  model_type,
  file_path,
  version,
  input_schema,
  metrics,
  is_active,
  imported_at
)

FORECAST(
  id PK,
  house_id FK -> HOUSE(id),
  model_id FK -> IMPORTED_MODEL(id) NULL,
  target,
  forecast_value,
  horizon_minutes,
  input_snapshot,
  created_at
)

DECISION(
  id PK,
  house_id FK -> HOUSE(id),
  forecast_id FK -> FORECAST(id) NULL,
  action,
  reason,
  confidence_score,
  input_snapshot,
  activated_rules,
  alert_level,
  risk_score,
  created_at
)

ALERT(
  id PK,
  house_id FK -> HOUSE(id),
  decision_id FK -> DECISION(id) NULL,
  severity,
  alert_type,
  message,
  is_read,
  created_at
)

DATA_EXPORT(
  id PK,
  user_id FK -> USER(id),
  house_id FK -> HOUSE(id),
  export_type,
  start_date,
  end_date,
  file_path,
  created_at
)
```

## 4. MPD - Modèle physique PostgreSQL

```sql
CREATE TABLE users_user (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(150),
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    phone VARCHAR(30),
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE users_emailverificationtoken (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE users_passwordresettoken (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE houses_house (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    location VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE energy_assets_energyasset (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    asset_type VARCHAR(30) NOT NULL,
    nominal_power_kw DOUBLE PRECISION,
    capacity_kwh DOUBLE PRECISION,
    voltage DOUBLE PRECISION,
    current DOUBLE PRECISION,
    efficiency DOUBLE PRECISION,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE devices_sensor (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    energy_asset_id BIGINT REFERENCES energy_assets_energyasset(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    sensor_type VARCHAR(30) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE devices_equipment (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    equipment_type VARCHAR(80),
    rated_power_kw DOUBLE PRECISION,
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE measurements_measurement (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    sensor_id BIGINT REFERENCES devices_sensor(id) ON DELETE SET NULL,
    measurement_type VARCHAR(30) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE forecasting_importedmodel (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    target VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT 'v1',
    input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE forecasting_forecast (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    model_id BIGINT REFERENCES forecasting_importedmodel(id) ON DELETE SET NULL,
    target VARCHAR(20) NOT NULL,
    forecast_value DOUBLE PRECISION NOT NULL,
    horizon_minutes INTEGER NOT NULL DEFAULT 60,
    input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE fuzzy_engine_decision (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    forecast_id BIGINT REFERENCES forecasting_forecast(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    reason TEXT,
    confidence_score DOUBLE PRECISION,
    input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    activated_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    alert_level VARCHAR(20),
    risk_score DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE alerts_alert (
    id BIGSERIAL PRIMARY KEY,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    decision_id BIGINT REFERENCES fuzzy_engine_decision(id) ON DELETE SET NULL,
    severity VARCHAR(20) NOT NULL,
    alert_type VARCHAR(40) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE reports_dataexport (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    house_id BIGINT NOT NULL REFERENCES houses_house(id) ON DELETE CASCADE,
    export_type VARCHAR(30) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    file_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_measurement_house_type_timestamp
ON measurements_measurement(house_id, measurement_type, timestamp DESC);

CREATE INDEX idx_sensor_asset
ON devices_sensor(energy_asset_id);

CREATE INDEX idx_forecast_house_created
ON forecasting_forecast(house_id, created_at DESC);

CREATE INDEX idx_decision_house_created
ON fuzzy_engine_decision(house_id, created_at DESC);

CREATE INDEX idx_alert_house_created
ON alerts_alert(house_id, created_at DESC);
```

## 5. Diagramme de classes UML

```mermaid
classDiagram
    class User {
        +id
        +username
        +email
        +role
        +phone
    }

    class House {
        +id
        +name
        +location
        +status
    }

    class EnergyAsset {
        +id
        +name
        +asset_type
        +nominal_power_kw
        +capacity_kwh
        +voltage
        +current
        +efficiency
        +status
        +metadata
    }

    class Sensor {
        +id
        +name
        +sensor_type
        +unit
        +is_active
    }

    class Equipment {
        +id
        +name
        +equipment_type
        +rated_power_kw
        +priority
        +status
    }

    class Measurement {
        +id
        +measurement_type
        +value
        +unit
        +timestamp
    }

    class ImportedModel {
        +id
        +name
        +target
        +model_type
        +version
        +input_schema
        +metrics
        +is_active
    }

    class Forecast {
        +id
        +target
        +forecast_value
        +horizon_minutes
        +input_snapshot
        +created_at
    }

    class Decision {
        +id
        +action
        +reason
        +confidence_score
        +input_snapshot
        +activated_rules
        +alert_level
        +risk_score
    }

    class Alert {
        +id
        +severity
        +alert_type
        +message
        +is_read
    }

    User "1" --> "0..*" House
    House "1" --> "0..*" EnergyAsset
    House "1" --> "0..*" Sensor
    House "1" --> "0..*" Equipment
    House "1" --> "0..*" Measurement
    EnergyAsset "1" --> "0..*" Sensor
    Sensor "1" --> "0..*" Measurement
    ImportedModel "1" --> "0..*" Forecast
    Forecast "0..1" --> "0..*" Decision
    Decision "0..1" --> "0..*" Alert
```

## 6. Diagramme de cas d'utilisation

```plantuml
@startuml
left to right direction
actor Utilisateur
actor Administrateur
actor "Système IoT" as IoT
actor "Edge Gateway" as Edge

rectangle "EMS" {
  usecase "S'inscrire" as UC1
  usecase "Se connecter" as UC2
  usecase "Vérifier e-mail" as UC3
  usecase "Réinitialiser mot de passe" as UC4
  usecase "Gérer maison / micro-réseau" as UC5
  usecase "Gérer actifs énergétiques" as UC6
  usecase "Gérer capteurs" as UC7
  usecase "Gérer équipements" as UC8
  usecase "Envoyer mesures MQTT" as UC9
  usecase "Consulter mesures" as UC10
  usecase "Importer modèle pré-entraîné" as UC11
  usecase "Lancer prévision" as UC12
  usecase "Déclencher décision floue" as UC13
  usecase "Recevoir alertes" as UC14
  usecase "Acquitter alertes" as UC15
  usecase "Exporter données" as UC16
  usecase "Consulter rapports" as UC17
}

Utilisateur --> UC1
Utilisateur --> UC2
Utilisateur --> UC3
Utilisateur --> UC4
Utilisateur --> UC5
Utilisateur --> UC10
Utilisateur --> UC12
Utilisateur --> UC14
Utilisateur --> UC15
Utilisateur --> UC17
Administrateur --> UC6
Administrateur --> UC7
Administrateur --> UC8
Administrateur --> UC11
Administrateur --> UC16
IoT --> UC9
Edge --> UC9
UC12 --> UC13
UC13 --> UC14
@enduml
```

## 7. Diagramme de séquence - collecte IoT

```plantuml
@startuml
actor "Capteur" as Sensor
participant "ESP32" as ESP
participant "MQTT Broker" as MQTT
participant "mqtt_handler" as Handler
participant "Backend API" as API
participant "Measurement Service" as MS
participant "PostgreSQL" as DB
participant "Dashboard" as UI

Sensor -> ESP : mesure tension/courant/puissance
ESP -> MQTT : publish JSON
MQTT -> Handler : message reçu
Handler -> API : validation payload
API -> MS : créer Measurement
MS -> DB : INSERT measurement
DB --> MS : OK
MS --> API : mesure enregistrée
API --> UI : données disponibles via API
@enduml
```

## 8. Diagramme de séquence - prévision et décision

```plantuml
@startuml
actor Utilisateur
participant "Frontend React" as Front
participant "Backend API" as API
participant "Measurement Service" as MS
participant "Forecasting Service" as FS
participant "Imported Model" as Model
participant "Fuzzy Engine" as FE
participant "Alert Service" as AS
participant "PostgreSQL" as DB

Utilisateur -> Front : Demander prévision
Front -> API : POST /api/forecasting/predict/
API -> MS : récupérer mesures récentes
MS -> DB : SELECT measurements
DB --> MS : mesures
MS --> API : données préparées
API -> FS : predict(house, target, horizon)
FS -> Model : inference(input_features)
Model --> FS : valeur prévue
FS -> DB : INSERT forecast
FS --> API : Forecast
API -> FE : evaluate(forecast, battery_soc, equipments)
FE --> API : Decision
API -> DB : INSERT decision
alt décision critique
    API -> AS : créer alerte
    AS -> DB : INSERT alert
end
API --> Front : forecast + decision + alert éventuelle
Front --> Utilisateur : afficher résultat
@enduml
```

## 9. Diagramme d'activité - système expert flou

```plantuml
@startuml
start
:Lire production prévue;
:Lire consommation prévue;
:Lire SoC batterie;
:Lire priorités des équipements;
:Lire état des actifs énergétiques;
:Fuzzification des entrées;
:Application des règles floues;
:Inférence;
:Défuzzification;
if (Situation critique ?) then (oui)
  :Décision de délestage ou alerte;
  :Créer alerte;
else (non)
  :Décision normale;
endif
:Enregistrer décision;
:Retourner action, raison, confiance;
stop
@enduml
```

## 10. Diagramme de composants backend

```plantuml
@startuml
package "Backend Django REST" {
  [Auth Service]
  [House Service]
  [Energy Asset Service]
  [Device Service]
  [Measurement Service]
  [Forecasting Service]
  [Fuzzy Decision Service]
  [Alert Service]
  [Report Export Service]
  [MQTT Handler]
}

database "PostgreSQL" as DB
queue "Mosquitto MQTT" as MQTT
cloud "Weather API optionnelle" as Weather

[MQTT Handler] --> MQTT
[MQTT Handler] --> [Measurement Service]
[Measurement Service] --> DB
[Forecasting Service] --> [Measurement Service]
[Forecasting Service] --> [Energy Asset Service]
[Forecasting Service] --> Weather
[Fuzzy Decision Service] --> [Forecasting Service]
[Fuzzy Decision Service] --> [Device Service]
[Alert Service] --> [Fuzzy Decision Service]
[Report Export Service] --> DB
[Auth Service] --> DB
[House Service] --> DB
[Energy Asset Service] --> DB
[Device Service] --> DB
@enduml
```

## 11. Diagramme de déploiement

```plantuml
@startuml
node "Utilisateur" {
  artifact "Navigateur Web"
  artifact "Application Mobile"
}

cloud "Vercel" {
  artifact "Frontend React"
}

cloud "AWS" {
  node "EC2 / ECS" {
    artifact "Backend Django REST"
    artifact "MQTT Worker"
  }
  database "RDS PostgreSQL" as RDS
  storage "S3" as S3
}

node "Maison / Micro-réseau" {
  artifact "ESP32"
  artifact "Capteurs"
  artifact "Raspberry Pi Edge Gateway"
  artifact "Mosquitto local"
}

"Navigateur Web" --> "Frontend React"
"Frontend React" --> "Backend Django REST"
"Application Mobile" --> "Backend Django REST"
"Application Mobile" --> "Raspberry Pi Edge Gateway" : mode local
"ESP32" --> "Mosquitto local" : MQTT
"Mosquitto local" --> "Raspberry Pi Edge Gateway"
"Raspberry Pi Edge Gateway" --> "Backend Django REST" : sync
"Backend Django REST" --> RDS
"Backend Django REST" --> S3
@enduml
```

## 12. Script de génération des diagrammes

Créer un dossier :

```bash
mkdir -p docs/diagrams/sources docs/diagrams/output
```

Installer Mermaid CLI :

```bash
npm install -g @mermaid-js/mermaid-cli
```

Installer PlantUML si Java est disponible :

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y default-jre plantuml graphviz
```

Exemple de script `docs/diagrams/generate_diagrams.sh` :

```bash
#!/usr/bin/env bash
set -e

mkdir -p docs/diagrams/output

# Mermaid
mmdc -i docs/diagrams/sources/mcd.mmd -o docs/diagrams/output/mcd.png
mmdc -i docs/diagrams/sources/class_diagram.mmd -o docs/diagrams/output/class_diagram.png

# PlantUML
plantuml -tpng -o ../output docs/diagrams/sources/use_case.puml
plantuml -tpng -o ../output docs/diagrams/sources/sequence_iot.puml
plantuml -tpng -o ../output docs/diagrams/sources/sequence_forecast_decision.puml
plantuml -tpng -o ../output docs/diagrams/sources/activity_fuzzy_engine.puml
plantuml -tpng -o ../output docs/diagrams/sources/component_backend.puml
plantuml -tpng -o ../output docs/diagrams/sources/deployment.puml

echo "Diagrammes générés dans docs/diagrams/output"
```

Rendre le script exécutable :

```bash
chmod +x docs/diagrams/generate_diagrams.sh
./docs/diagrams/generate_diagrams.sh
```

## 13. Liste des diagrammes à insérer dans le mémoire

```text
1. Diagramme de contexte du système EMS
2. Diagramme de cas d'utilisation
3. Diagramme de classes UML
4. MCD Merise
5. MLD
6. MPD PostgreSQL
7. Diagramme de séquence de collecte IoT
8. Diagramme de séquence prévision-décision
9. Diagramme d'activité du système expert flou
10. Diagramme de composants backend
11. Diagramme de déploiement Edge-Cloud
```

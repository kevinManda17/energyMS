# EMS - Diagrammes actuels de la base de donnees

Date de reference : 2026-07-03

Source : modeles Django charges via `ems-backend/manage.py` et base locale `ems-backend/db.sqlite3`.

Ce document decrit le schema applicatif actuel. Les tables techniques Django (`auth_group`, `auth_permission`, `django_content_type`, `django_admin_log`, `django_session`, `django_migrations`) existent aussi dans la base, mais elles sont gardees a part pour ne pas rendre le diagramme illisible.

## Lecture rapide

Le centre du modele est `HOUSE`.

```text
USER
  -> HOUSE
      -> ENERGY_ASSET
      -> SENSOR
      -> EQUIPMENT
      -> MEASUREMENT
      -> FORECAST
      -> DECISION
      -> ALERT
      -> DATA_EXPORT

IMPORTED_MODEL -> FORECAST -> DECISION -> ALERT
ENERGY_ASSET -> SENSOR -> MEASUREMENT
```

Les changements importants par rapport a l'ancien schema :

- `Dataset` existe maintenant pour les imports CSV/JSON internes.
- `PhoneVerificationCode`, `EmailVerificationToken` et `PasswordResetToken` sont dans le module `users`.
- `ImportedModel` contient les champs ML recents : `file`, `preprocessing_path`, `sequence_length`, `feature_columns`.
- `Forecast.house_id` et `Forecast.model_id` sont optionnels.
- `Decision` contient maintenant beaucoup de champs d'inference floue avances.
- `User` garde les tables M2M Django `users_user_groups` et `users_user_user_permissions`.

## MCD / ERD

```mermaid
erDiagram
    USER ||--o{ HOUSE : owns
    USER ||--o{ EMAIL_VERIFICATION_TOKEN : verifies_email
    USER ||--o{ PASSWORD_RESET_TOKEN : resets_password
    USER ||--o{ DATASET : uploads
    USER ||--o{ DATA_EXPORT : requests

    HOUSE ||--o{ ENERGY_ASSET : contains
    HOUSE ||--o{ SENSOR : has
    HOUSE ||--o{ EQUIPMENT : has
    HOUSE ||--o{ MEASUREMENT : receives
    HOUSE ||--o{ FORECAST : has
    HOUSE ||--o{ DECISION : has
    HOUSE ||--o{ ALERT : has
    HOUSE ||--o{ DATA_EXPORT : exports

    ENERGY_ASSET ||--o{ SENSOR : measured_by
    SENSOR ||--o{ MEASUREMENT : produces
    IMPORTED_MODEL ||--o{ FORECAST : generates
    FORECAST ||--o{ DECISION : feeds
    DECISION ||--o{ ALERT : creates

    USER {
        bigint id PK
        varchar username UK
        varchar email UK
        varchar role
        varchar phone
        bool phone_verified
        bool email_verified
        json preferences
        datetime created_at
    }

    PHONE_VERIFICATION_CODE {
        bigint id PK
        varchar phone
        varchar code_hash
        datetime expires_at
        int attempts
        datetime used_at
        datetime created_at
    }

    EMAIL_VERIFICATION_TOKEN {
        bigint id PK
        bigint user_id FK
        varchar token_hash
        datetime expires_at
        datetime used_at
        datetime created_at
    }

    PASSWORD_RESET_TOKEN {
        bigint id PK
        bigint user_id FK
        varchar token_hash
        datetime expires_at
        datetime used_at
        datetime created_at
    }

    HOUSE {
        bigint id PK
        bigint owner_id FK
        varchar name
        varchar location
        float latitude
        float longitude
        text description
        varchar status
        datetime created_at
        datetime updated_at
    }

    ENERGY_ASSET {
        bigint id PK
        bigint house_id FK
        varchar name
        varchar asset_type
        float nominal_power_kw
        float capacity_kwh
        float voltage
        float current
        float efficiency
        varchar status
        json metadata
    }

    SENSOR {
        bigint id PK
        bigint house_id FK
        bigint energy_asset_id FK
        varchar name
        varchar sensor_type
        varchar unit
        bool is_active
    }

    EQUIPMENT {
        bigint id PK
        bigint house_id FK
        varchar name
        varchar equipment_type
        float rated_power_kw
        varchar priority
        varchar status
    }

    MEASUREMENT {
        bigint id PK
        bigint house_id FK
        bigint sensor_id FK
        varchar measurement_type
        float value
        varchar unit
        datetime timestamp
    }

    DATASET {
        bigint id PK
        bigint uploaded_by_id FK
        varchar name
        varchar kind
        varchar file
        varchar status
        int rows
        json columns
        text message
    }

    IMPORTED_MODEL {
        bigint id PK
        varchar name
        varchar target
        varchar model_type
        varchar file
        varchar file_path
        varchar preprocessing_path
        int sequence_length
        json feature_columns
        varchar version
        json input_schema
        json metrics
        bool is_active
    }

    FORECAST {
        bigint id PK
        bigint house_id FK
        bigint model_id FK
        varchar target
        datetime horizon
        int horizon_minutes
        float forecast_value
        json input_snapshot
        datetime created_at
    }

    DECISION {
        bigint id PK
        bigint house_id FK
        bigint forecast_id FK
        varchar action
        text reason
        float confidence_score
        varchar decision_code
        varchar decision_label
        varchar execution_mode
        varchar alert_level
        float risk_score
        float shedding_level
        varchar battery_action
        text explanation
        json fired_rules
        json input_facts
        json fuzzy_values
        datetime created_at
    }

    ALERT {
        bigint id PK
        bigint house_id FK
        bigint decision_id FK
        varchar severity
        varchar alert_type
        text message
        bool is_read
        datetime created_at
    }

    DATA_EXPORT {
        bigint id PK
        bigint user_id FK
        bigint house_id FK
        varchar export_type
        datetime start_date
        datetime end_date
        varchar file_path
        datetime created_at
    }
```

## MLD

```text
USER(
  id PK,
  password,
  last_login NULL,
  is_superuser,
  username UNIQUE,
  first_name,
  last_name,
  is_staff,
  is_active,
  date_joined,
  email UNIQUE,
  role,
  phone,
  phone_verified,
  email_verified,
  preferences,
  created_at
)

PHONE_VERIFICATION_CODE(
  id PK,
  phone INDEX,
  code_hash,
  expires_at,
  attempts,
  used_at NULL,
  created_at
)

EMAIL_VERIFICATION_TOKEN(
  id PK,
  user_id FK -> USER(id),
  token_hash,
  expires_at,
  used_at NULL,
  created_at
)

PASSWORD_RESET_TOKEN(
  id PK,
  user_id FK -> USER(id),
  token_hash,
  expires_at,
  used_at NULL,
  created_at
)

HOUSE(
  id PK,
  owner_id FK -> USER(id),
  name,
  location,
  latitude NULL,
  longitude NULL,
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
  nominal_power_kw NULL,
  capacity_kwh NULL,
  voltage NULL,
  current NULL,
  efficiency NULL,
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

DATASET(
  id PK,
  uploaded_by_id FK -> USER(id) NULL,
  name,
  kind,
  file,
  status,
  rows,
  columns,
  message,
  created_at
)

IMPORTED_MODEL(
  id PK,
  name,
  target,
  model_type,
  file NULL,
  file_path,
  preprocessing_path,
  sequence_length,
  feature_columns,
  version,
  input_schema,
  metrics,
  is_active,
  imported_at
)

FORECAST(
  id PK,
  house_id FK -> HOUSE(id) NULL,
  model_id FK -> IMPORTED_MODEL(id) NULL,
  target,
  horizon,
  horizon_minutes,
  forecast_value,
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
  decision_code,
  decision_label,
  execution_mode,
  alert_level,
  risk_score,
  shedding_level,
  charge_battery_score,
  discharge_battery_score,
  protect_battery_score,
  recommendation_score,
  automatic_score,
  blocked_score,
  battery_action,
  explanation,
  fired_rules,
  input_facts,
  fuzzy_values,
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
  start_date NULL,
  end_date NULL,
  file_path,
  created_at
)

USER_GROUPS(
  id PK,
  user_id FK -> USER(id),
  group_id FK -> AUTH_GROUP(id),
  UNIQUE(user_id, group_id)
)

USER_USER_PERMISSIONS(
  id PK,
  user_id FK -> USER(id),
  permission_id FK -> AUTH_PERMISSION(id),
  UNIQUE(user_id, permission_id)
)
```

## MPD

Noms physiques des tables applicatives :

```text
users_user
users_phoneverificationcode
users_emailverificationtoken
users_passwordresettoken
houses_house
energy_assets_energyasset
devices_sensor
devices_equipment
measurements_measurement
datasets_dataset
forecasting_importedmodel
forecasting_forecast
fuzzy_engine_decision
alerts_alert
reports_dataexport
```

Tables techniques Django liees :

```text
users_user_groups
users_user_user_permissions
auth_group
auth_group_permissions
auth_permission
django_content_type
django_admin_log
django_session
django_migrations
```

Index principaux declares dans les modeles :

```text
users_phoneverificationcode(phone)

energy_assets_energyasset(house_id, asset_type)
energy_assets_energyasset(status)

measurements_measurement(house_id, measurement_type, timestamp DESC)
measurements_measurement(sensor_id, timestamp DESC)
measurements_measurement(timestamp)

forecasting_importedmodel(target, is_active)
forecasting_importedmodel(model_type)
forecasting_forecast(house_id, created_at)
forecasting_forecast(house_id, target, horizon)

fuzzy_engine_decision(created_at)
alerts_alert(created_at)
```

Toutes les clefs etrangeres Django generent aussi des index physiques dans SQLite/PostgreSQL.

## Diagramme de classes UML

```mermaid
classDiagram
    class User {
        +id
        +username
        +email
        +role
        +phone
        +phone_verified
        +email_verified
        +preferences
    }

    class PhoneVerificationCode {
        +id
        +phone
        +code_hash
        +expires_at
        +attempts
        +used_at
    }

    class EmailVerificationToken {
        +id
        +token_hash
        +expires_at
        +used_at
    }

    class PasswordResetToken {
        +id
        +token_hash
        +expires_at
        +used_at
    }

    class House {
        +id
        +name
        +location
        +latitude
        +longitude
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

    class Dataset {
        +id
        +name
        +kind
        +file
        +status
        +rows
        +columns
    }

    class ImportedModel {
        +id
        +name
        +target
        +model_type
        +file_path
        +preprocessing_path
        +sequence_length
        +feature_columns
        +metrics
        +is_active
    }

    class Forecast {
        +id
        +target
        +horizon
        +horizon_minutes
        +forecast_value
        +input_snapshot
    }

    class Decision {
        +id
        +action
        +reason
        +confidence_score
        +decision_code
        +alert_level
        +risk_score
        +shedding_level
        +battery_action
        +fired_rules
        +fuzzy_values
    }

    class Alert {
        +id
        +severity
        +alert_type
        +message
        +is_read
    }

    class DataExport {
        +id
        +export_type
        +start_date
        +end_date
        +file_path
    }

    User "1" --> "0..*" House
    User "1" --> "0..*" EmailVerificationToken
    User "1" --> "0..*" PasswordResetToken
    User "0..1" --> "0..*" Dataset
    User "1" --> "0..*" DataExport

    House "1" --> "0..*" EnergyAsset
    House "1" --> "0..*" Sensor
    House "1" --> "0..*" Equipment
    House "1" --> "0..*" Measurement
    House "0..1" --> "0..*" Forecast
    House "1" --> "0..*" Decision
    House "1" --> "0..*" Alert
    House "1" --> "0..*" DataExport

    EnergyAsset "0..1" --> "0..*" Sensor
    Sensor "0..1" --> "0..*" Measurement
    ImportedModel "0..1" --> "0..*" Forecast
    Forecast "0..1" --> "0..*" Decision
    Decision "0..1" --> "0..*" Alert
```

## Generation en image

Les sources Mermaid sont aussi sorties ici :

```text
docs/diagrams/sources/database_current_erd.mmd
docs/diagrams/sources/database_current_class.mmd
docs/diagrams/sources/database_current_erd.dot
```

Commande possible si Mermaid CLI est disponible :

```bash
mkdir -p docs/diagrams/output
npx @mermaid-js/mermaid-cli -i docs/diagrams/sources/database_current_erd.mmd -o docs/diagrams/output/database_current_erd.svg
npx @mermaid-js/mermaid-cli -i docs/diagrams/sources/database_current_class.mmd -o docs/diagrams/output/database_current_class.svg
```

Rendu Graphviz local :

```bash
mkdir -p docs/diagrams/output
dot -Tsvg docs/diagrams/sources/database_current_erd.dot -o docs/diagrams/output/database_current_erd_graphviz.svg
dot -Tpng docs/diagrams/sources/database_current_erd.dot -o docs/diagrams/output/database_current_erd_graphviz.png
```

Rendus deja generes :

```text
docs/diagrams/output/database_current_erd_graphviz.svg
docs/diagrams/output/database_current_erd_graphviz.png
```

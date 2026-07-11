# Architecture EMS

## Vue globale

La plateforme EMS est un ecosysteme IoT de gestion intelligente de l'energie pour micro-reseau domestique. Elle est centree sur la chaine suivante :

```text
collecte IoT -> mesures -> modeles pre-entraines importes -> prevision -> decision floue -> alerte -> supervision web/mobile
```

Le backend n'est pas une plateforme d'entrainement Machine Learning. Les modeles sont entraines hors plateforme, puis importes dans EMS pour l'inference sur les donnees collectees.

```text
Noeud ESP32 (prototype 3 lignes)
   -> HTTP POST /api/ems/decision/  (releve tension/courant/puissance par ligne)
   -> Measurements (consommation/tension/courant) + PostgreSQL
   -> Forecasting inference (modeles enregistres) + Open-Meteo
   -> Fuzzy engine (decision sur mesures reelles)
   -> reponse "L1=x;L2=x;L3=x" -> relais -> charges
   -> Alerts / Reports -> React Web + React Native

Voie MQTT (disponible, non utilisee par le prototype actuel)
   Capteurs -> MQTT Mosquitto -> mqtt_worker Django -> Measurements

Edge Gateway (module present, non integre a la demo)
   -> cache SQLite local -> synchronisation differee vers l'API
```

## Modules backend

| App | Role |
| --- | --- |
| `users` | Auth JWT, roles USER/ADMIN, profil, verification telephone, verification e-mail, reset password. |
| `houses` | Maisons / micro-reseaux comme sites logiques. |
| `energy_assets` | Actifs energetiques physiques : PV, batterie, onduleur, regulateur, reseau, generateur. |
| `devices` | Capteurs et equipements/charges. Les capteurs peuvent pointer vers un `EnergyAsset`. |
| `measurements` | Mesures IoT : production, consommation, SoC batterie, tension, courant, puissance, temperature, luminosite, irradiance. |
| `forecasting` | Modeles pre-entraines enregistres (`register_models`), inference (GRU/RF actifs), stockage des `Forecast`. Pas de repli mathematique. |
| `fuzzy_engine` | Systeme expert flou, decisions explicables, lien vers la prevision utilisee. |
| `alerts` | Alertes critiques/warning/info, lien possible vers une decision. |
| `reports` | Rapports journaliers, exports CSV et historique `DataExport`. |
| `mqtt_handler` | Souscripteur MQTT + validation/persistance des mesures. |
| `datasets` | Module admin/interne conserve pour compatibilite, hors parcours utilisateur et hors entrainement backend. |

## Modele metier

```text
User -> House
House -> EnergyAsset
House -> Sensor -> Measurement
House -> Equipment
House -> Forecast -> Decision -> Alert
User -> DataExport
```

`House` represente le site logique. Les caracteristiques physiques de production, stockage ou conversion sont portees par `EnergyAsset`.

## Flux IoT

1. Un capteur publie sur `ems/{house_id}/sensors/{sensor_id}/data`.
2. Le payload contient au minimum `type`, `value`, `unit`, `timestamp`, et peut contenir `sensor_id`.
3. `mqtt_worker` valide le payload et cree une `Measurement`.
4. L'Edge Gateway peut mettre les mesures en cache SQLite et les synchroniser plus tard.
5. Le web et le mobile lisent les mesures via l'API REST ou l'API locale edge.

## Flux prevision

1. Un administrateur importe un modele pre-entraine via `/api/forecasting/models/import/`.
2. L'utilisateur ou le systeme demande une prevision via `/api/forecasting/predict/`.
3. Le service prepare les entrees depuis les mesures recentes et les actifs energetiques.
4. Le modele actif (GRU pour la consommation, RF pour la production) execute l'inference.
5. En l'absence de modele actif, une erreur explicite est levee (pas de prevision de repli).
6. Les resultats sont stockes dans `Forecast`.

## Flux decision (sur donnees reelles)

1. `/api/decisions/trigger/` lit les **dernieres mesures reelles**, les previsions et les equipements actifs du micro-reseau.
2. Le moteur flou (`engine.py` -> `core/`) evalue les 24 regles et produit une `Decision` explicable (regles activees, scores, faits d'entree).
3. La decision peut etre reliee a un `Forecast`.
4. Une alerte est creee pour les situations critiques ou warning.

## Flux commande (backend -> ESP32)

1. Depuis le web/mobile, l'utilisateur bascule une ligne via `PATCH /api/houses/{id}/relays/`.
2. Le noeud ESP32 (mode auto) sonde `/api/ems/decision/` toutes les ~3 s.
3. Le backend renvoie l'etat commande `L1=x;L2=x;L3=x` ; l'ESP32 applique les relais (garde-fou de puissance local en surcouche).

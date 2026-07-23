# État courant du système — EMS IoT

> **Règle de tenue à jour** : toute modification du câblage, des broches, des
> variables réseau, des modèles de données ou des unités doit être répercutée
> **immédiatement** dans ce fichier. Un document qui décrit une version passée
> est pire qu'un document absent : il fait perdre du temps et induit en erreur.
>
> Vérification automatique : `python scripts/audit_config.py --strict`

Dernière mise à jour : **19/07/2026**

---

## 1. Câblage ESP32 (état validé — ne pas revenir en arrière)

### Relais (module 8 canaux, 3 utilisés)

| Ligne | GPIO ESP32 | Entrée module | Canal / contacts |
|-------|-----------|---------------|------------------|
| Ligne 1 | **G25** | **IN2** | CH2 — COM2 / NO2 |
| Ligne 2 | **G26** | **IN3** | CH3 — COM3 / NO3 |
| Ligne 3 | **G27** | **IN6** | CH6 — COM6 / NO6 |

> ⚠ La ligne 1 est sur **IN2 / COM2 / NO2** depuis le recâblage. Toute doc qui
> mentionne encore IN1 / COM1 / NO1 pour la ligne 1 est **obsolète**.

Seul le **GPIO** figure dans `config.h` : déplacer un fil vers un autre canal du
module ne demande aucun changement de code tant que le GPIO reste le même.

`RELAY_ACTIVE_LOW = false` — le module s'est révélé **actif à HIGH**. C'est le
seul endroit qui traduit « ligne active » en niveau électrique ; ne jamais
compenser une inversion côté interface (la protection surcharge s'inverserait).

### Capteurs analogiques (sorties ≤ 3,3 V impératif)

| Code | Capteur | Grandeur | GPIO |
|------|---------|----------|------|
| `V1` | ZMPT101B-1 | Tension L1 | G34 |
| `I1` | ZMCT103C-1 | Courant L1 | G35 |
| `V2` | ZMPT101B-2 | Tension L2 | G32 |
| `I2` | ZMCT103C-2 | Courant L2 | G33 |
| `V3` | ZMPT101B-3 | Tension L3 | G36 (SP / SVP) |
| `I3` | ZMCT103C-3 | Courant L3 | G39 (SN / SVN) |

Chaque capteur porte un **code stable** (`V1`, `I1`…) exploité par l'application
et la calibration. La puissance n'est pas un capteur : elle est **calculée**
(`V1 × I1 → puissance ligne 1`). Détail complet et méthode de calibration :
[SENSORS_AND_CALIBRATION.md](SENSORS_AND_CALIBRATION.md).

Création en base : `python manage.py seed_prototype --house <id>` (idempotent).

Tous sur l'**ADC1** : fonctionnels même Wi-Fi actif. G34/G35/G36/G39 sont des
**entrées seulement**. Broches interdites : CMD, SD0-SD3, CLK (flash interne).

---

## 2. Charges par ligne

| Ligne | Charges (en parallèle) | Priorités |
|-------|------------------------|-----------|
| Ligne 1 | Lampe L1 (10 W) + Prise 1 | normale / non prioritaire |
| Ligne 2 | **Lampe L2 (20 W) seule** | prioritaire |
| Ligne 3 | Lampe L3 (10 W) + Prise 2 | normale / non prioritaire |

Une ligne **n'est pas réductible à une seule charge** : les lignes 1 et 3 en
portent deux, en parallèle. Couper la ligne 1 coupe la lampe *et* la prise 1.
Les charges sont enregistrées comme `Equipment` (`load_type` = lamp/socket,
`relay_line`, `priority`).

### Priorité des charges — 5 niveaux

Le modèle `Equipment.priority` définit **cinq niveaux**, du plus protégé au plus
délestable. Ils sont sélectionnables à la création d'une charge (web en lecture,
formulaire mobile) :

| Niveau | Libellé | Rôle |
|--------|---------|------|
| `CRITICAL` | Critique | jamais coupée automatiquement |
| `IMPORTANT` | Important | prioritaire |
| `NORMAL` | Normal | charge courante (défaut) |
| `LOW` | Secondaire | délestée avant une charge normale |
| `NON_CRITICAL` | Non critique | délestée **en premier** |

> **La décision regroupe ces 5 niveaux en 3 catégories** (`_load_priority`), car
> le moteur flou n'a besoin que de savoir s'il doit **protéger**, **recommander**
> ou peut **délester** :
> `CRITICAL → CRITICAL` · `IMPORTANT, NORMAL → PRIORITY` · `LOW, NON_CRITICAL → NON_PRIORITY`.
> Les 5 niveaux restent visibles côté données et interfaces ; seul le
> raisonnement décisionnel les regroupe. Le classement de délestage
> (`actuator.PRIORITY_RANK`), lui, distingue bien les 5.

> **À corriger dans le mémoire** (§4.4.2) : le texte décrit la priorité en trois
> niveaux « faible / moyenne / élevée ». La taxonomie réelle est celle des cinq
> niveaux ci-dessus. Signalé, non encore répercuté dans le PDF.

> **Écart signalé et tranché (19/07/2026)** : le cahier des charges annonçait
> L2 = 10 W + prise 2 et L3 = 20 W. Après vérification, le mapping **ci-dessus
> a été confirmé** : la lampe 20 W est bien sur la **ligne 2**. Le code (web et
> mobile) est cohérent avec ce tableau. Aucune inversion automatique n'a été
> appliquée.

### Procédure de vérification physique (à refaire après tout recâblage)

1. Mettre le micro-réseau en mode **Manuel** (page Équipements).
2. Couper la **Ligne 1** → seule la lampe 10 W + prise 1 doit s'éteindre.
3. Rétablir, couper la **Ligne 2** → seule la lampe 20 W doit s'éteindre.
4. Rétablir, couper la **Ligne 3** → seule la lampe 10 W + prise 2 doit s'éteindre.
5. Si une ligne éteint la mauvaise charge : corriger **ce tableau** et les
   libellés `RELAY_LINES` (frontend + mobile) — pas le câblage GPIO.

Équivalent au moniteur série (115200 bauds) : `on 1` / `off 1`, `on 2` / `off 2`,
`on 3` / `off 3`.

---

## 3. Réseau

| Élément | Valeur |
|---------|--------|
| Adresse LAN du PC | `192.168.0.117` |
| Backend (écoute) | `0.0.0.0:8000` (toutes interfaces) |
| Backend (accès) | `http://192.168.0.117:8000` |
| Frontend | `http://192.168.0.117:5173` |
| API | `http://192.168.0.117:8000/api` |
| Endpoint ESP32 | `http://192.168.0.117:8000/api/ems/decision/` |

`localhost` / `127.0.0.1` restent acceptés **uniquement** comme repli de
développement sur le PC lui-même. Un téléphone ou l'ESP32 ne peuvent pas les
joindre : `localhost` y désigne l'appareil lui-même.

**L'adresse LAN change à chaque réseau.** Pour la retrouver et propager :

```bash
python scripts/configure_lan.py           # affiche
python scripts/configure_lan.py --write   # met à jour les .env de dev
```

Le script ne peut pas mettre à jour l'ESP32 (il faut reflasher) : changer
`BACKEND_HOST_STR` dans `esp32-firmware/arduino/EMS_ESP32/config.h`.

### Où l'adresse est définie (une seule fois par composant)

| Composant | Variable / constante | Repli |
|-----------|---------------------|-------|
| Backend | `LAN_HOST` (settings/base.py) | `192.168.0.117` |
| Frontend | `VITE_API_BASE_URL` (.env) | hôte de la page + `:8000/api` |
| Mobile | `EXPO_PUBLIC_API_BASE_URL` (.env) | `192.168.0.117` en dur |
| ESP32 | `BACKEND_HOST_STR` (config.h) | aucun — recompilation requise |

Le frontend est le seul à savoir s'adapter seul : il déduit l'API de l'hôte de
la page (`src/api/baseUrl.js`). Valable si backend et frontend sont sur la même
machine. Le mobile et l'ESP32 n'ont aucun moyen fiable de deviner l'adresse.

---

## 4. Variables d'environnement

### Backend (`ems-backend/.env`)

```env
LAN_HOST=192.168.0.117
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
API_BASE_URL=http://192.168.0.117:8000/api
FRONTEND_BASE_URL=http://192.168.0.117:5173
PUBLIC_APP_BASE_URL=http://192.168.0.117:5173
DJANGO_ALLOWED_HOSTS=192.168.0.117,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://192.168.0.117:5173,http://localhost:5173
DJANGO_SECRET_KEY=<au moins 32 octets — sert aussi à signer les JWT>
EMS_AUTO_CONFIRM_SECONDS=180
```

### Frontend (`ems-frontend/.env`)

```env
VITE_API_BASE_URL=http://192.168.0.117:8000/api
VITE_WS_URL=ws://192.168.0.117:8000/ws
```

### Mobile (`ems-mobile/.env`)

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.117:8000/api
EXPO_PUBLIC_EDGE_API_URL=http://192.168.0.117:8000/api
```

---

## 5. Unités — règle stricte

| Grandeur | Unité | Où |
|----------|-------|-----|
| Puissance instantanée brute | **W** | calculée par l'ESP32 (`U × I`), stockée en `power` |
| Puissance instantanée normalisée | **kW** | `consumption` = `power / 1000` |
| Énergie cumulée | **kWh** | intégration de la puissance dans le temps |

> **Corrigé le 19/07/2026** : le backend stockait la somme des watts de l'ESP32
> directement sous l'unité `kW`. 40 W devenaient donc « 40 kW » — une erreur d'un
> facteur 1000 qui faussait le moteur expert et les tableaux de bord. La
> conversion est désormais explicite (`WATTS_PER_KILOWATT`).
>
> ⚠ **Les mesures enregistrées AVANT cette correction restent fausses d'un
> facteur 1000.** Elles n'ont pas été rétro-corrigées (impossible de distinguer
> a posteriori les valeurs déjà correctes). En tenir compte dans toute analyse
> d'historique.

Ne jamais additionner des puissances et appeler le résultat une énergie : il
faut multiplier par la durée (`kWh = kW × heures`).

---

## 6. Calibration des capteurs

**État : NON CALIBRÉE.** `CAL_V1..V3` et `CAL_I1..I3` valent `1.0` — le système
affiche donc le **RMS brut de la sortie du capteur** (en volts ADC), pas des
volts/ampères réels.

C'est un choix assumé : mieux vaut une valeur brute reconnue comme telle qu'un
chiffre inventé. **Aucune valeur n'est plafonnée ni forcée** — un plafonnement à
`[215, 224] V` a existé puis a été retiré le 19/07/2026, car il masquait les
fluctuations réelles et rendait les trois lignes identiques.

### Méthode (tension) — à refaire pour CHAQUE ligne

1. Mesurer la tension réelle de la ligne au multimètre (ex. 217 V).
2. Lire la tension affichée par l'ESP32 pour cette même ligne.
3. `nouveau_CAL_Vx = CAL_Vx_actuel × (tension_multimètre / tension_affichée)`
4. Téléverser, vérifier, répéter une fois si l'écart persiste.

### Méthode (courant) — avec une charge connue

1. Brancher une charge de puissance connue (lampe 20 W sous ~220 V).
2. Courant attendu ≈ `P / U` (20 / 220 ≈ 0,09 A).
3. `nouveau_CAL_Ix = CAL_Ix_actuel × (courant_attendu / courant_affiché)`

Chaque capteur a son propre potentiomètre : les trois lignes ont donc des
coefficients **différents**. Ne plus toucher au potentiomètre après calibration.
Le résultat attendu : si L1 fluctue à 217 V, L2 à 224 V et L3 à 210 V, le
système affiche 217 / 224 / 210 — et non trois fois la même valeur.

---

## 7. Températures — ne pas confondre

| Type de mesure | Source | Usage |
|----------------|--------|-------|
| `temperature` | **API météo** (Open-Meteo, `temperature_2m`) | température **ambiante** de l'air |
| `battery_temp` | sonde dédiée — **non installée** | température batterie (système expert) |
| `panel_temp` | sonde dédiée — **non installée** | température panneau |
| `module_temp` | jeu de données PV | température module (modèle de prévision) |

> **Corrigé le 19/07/2026** : le système expert lisait `temperature` (la météo)
> comme température de batterie. Les règles thermiques batterie (R001, R002)
> pouvaient donc se déclencher sur la météo du jour. Le moteur lit désormais
> `battery_temp` uniquement ; sans sonde, il retient 25 °C (valeur neutre) et
> les règles thermiques restent inactives — c'est voulu et assumé.

**Extension prévue (non installée à ce jour)** : sondes DS18B20 sur le panneau
solaire, la batterie 1, la batterie 2, et la future batterie lithium.

---

## 8. Prévision — ce que les modèles prédisent réellement

| Modèle | Cible | Pas natif | Nature |
|--------|-------|-----------|--------|
| GRU (Keras) | consommation | **10 min** | puissance au pas suivant |
| Random Forest | production PV | **10 min** | puissance à l'horizon demandé |

Les deux ont été entraînés sur une cadence **10 minutes** pour prédire **le pas
suivant** — pas « la valeur dans une heure ».

- Le GRU procède par **rollout autorégressif** : chaque point est réinjecté dans
  la fenêtre pour prédire le suivant. L'erreur s'accumule donc avec l'horizon ;
  une prévision à 1 h (6 pas) est moins fiable qu'à 10 min.
- Le Random Forest est **plat** : chaque horizon est prédit depuis la météo
  prévue pour cet horizon, sans fenêtre historique — pas d'accumulation d'erreur.

**Passage puissance → énergie.** `_prediction_energy()` (fuzzy_engine/engine.py)
intègre correctement : chaque point est pondéré par l'écart de temps jusqu'au
suivant (`kWh = Σ P_i × Δt_i`), et non sommé brutalement. Sommer 6 puissances
sans multiplier par la durée donnerait une valeur 6× trop grande.

**Limite assumée** : aucun modèle multi-horizon (t+10…t+60) n'est entraîné. Une
prévision à 1 h reste une extrapolation du modèle à 10 min.

---

## 9. Fonctionnalités — état réel

### Réalisé

- Chaîne temps réel ESP32 → backend → interfaces (sondage 3 s, mesures 30 s).
- Système expert flou : 24 règles, fuzzification, inférence, agrégation, mapping.
- Boucle fermée décision → relais, avec 3 modes : `MANUAL`, `ASSISTED`, `AUTO`.
- Fenêtre de confirmation en mode AUTO (180 s) : pas de coupure sur transitoire.
- Mappage charge ↔ ligne (`Equipment.relay_line`) ; ligne critique jamais coupée.
- Interface de test du système expert (injection manuelle de faits).
- Prévision ML (GRU consommation, RF production) avec météo Open-Meteo.
- Géolocalisation de la maison (web + mobile).

### Non réalisé / limites connues

- **Calibration des capteurs** : non faite. Les valeurs affichées ne sont pas
  encore des volts/ampères réels. Prérequis à toute exploitation du mode `AUTO`.
- **Sondes de température** (DS18B20) : non installées.
- **Mesure PV et batterie** : le prototype ne mesure que 3 lignes de
  consommation. Production et SOC viennent d'autres sources ou de valeurs par
  défaut — le système expert raisonne donc sur des données partielles.
- **Historique de mesures antérieur au 19/07/2026** : consommations fausses d'un
  facteur 1000 (voir §5).
- **ESP32** : l'adresse du backend impose une recompilation. Configuration par
  série / NVS / mDNS envisagée, non implémentée.

---

## 10. Lancement

```bash
# Backend — écoute sur toutes les interfaces
cd ems-backend
python manage.py runserver 0.0.0.0:8000

# Frontend — accessible depuis le réseau
cd ems-frontend
npm run dev -- --host 0.0.0.0

# Mobile
cd ems-mobile
npx expo start --clear
```

Pare-feu Windows : ouvrir les ports 8000, 5173 et 8081 (Metro) sur le profil du
réseau courant — voir `ems-backend/open-lan-ports.ps1` (PowerShell administrateur).

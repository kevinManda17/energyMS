# EMS ESP32 — Firmware « 3 lignes »

Firmware du prototype IoT du système EMS : mesure de tension/courant sur
3 lignes AC et commande de 3 relais, en mode manuel (port série) ou
automatique (règles locales de secours, ou système expert backend via HTTP).

```
esp32-firmware/
└── arduino/
    └── EMS_ESP32/      # firmware, pour l'IDE Arduino
        ├── EMS_ESP32.ino
        └── config.h    # pins, calibration, seuils, Wi-Fi
```

> Le projet a compté un second exemplaire du firmware pour PlatformIO
> (`platformio.ini`, `src/main.cpp`, `include/config.h`). Il a été supprimé :
> les deux copies devaient être tenues à jour en parallèle, et celle de
> PlatformIO avait fini par diverger (Wi-Fi désactivé, SSID resté factice).
> Une seule source fait foi désormais : `arduino/EMS_ESP32/`.

## Câblage (NE PAS MODIFIER SANS REVALIDER)

### Relais (module 8 canaux, 3 utilisés)

| GPIO ESP32 | Entrée module | Canal | Ligne |
|-----------|---------------|-------|-------|
| G25 | IN2 | CH2 (COM2/NO2) | Ligne 1 |
| G26 | IN3 | CH3 (COM3/NO3) | Ligne 2 |
| G27 | IN6 | CH6 (COM6/NO6) | Ligne 3 |

Seul le **GPIO** figure dans `config.h` (`RELAY_L1_PIN`…) : changer de canal sur
le module (IN2 plutôt que IN1, etc.) ne demande aucune modification du code tant
que le fil reste sur le même GPIO côté ESP32 — mettre à jour ce tableau suffit.

Ce module s'est révélé **actif à HIGH** : `RELAY_ACTIVE_LOW = false` dans
`config.h`. Cette constante est le **seul** endroit qui traduit « ligne active »
en niveau électrique. Si les relais fonctionnent à l'envers, c'est ici qu'on
corrige — jamais dans le frontend, le mobile ou le backend, où `true` = ligne
sous tension : la protection surcharge écrit `false` pour **couper**, et
s'inverserait elle aussi.

### Capteurs analogiques

| Capteur | Sortie | GPIO ESP32 |
|---------|--------|-----------|
| ZMPT101B‑1 (tension L1) | OUT | G34 |
| ZMCT103C‑1 (courant L1) | OUT | G35 |
| ZMPT101B‑2 (tension L2) | OUT | G32 |
| ZMCT103C‑2 (courant L2) | OUT | G33 |
| ZMPT101B‑3 (tension L3) | OUT | SP = GPIO36 |
| ZMCT103C‑3 (courant L3) | OUT | SN = GPIO39 |

**Règles impératives :**

- Les sorties OUT des capteurs doivent rester **≤ 3,3 V** (régler les
  potentiomètres des ZMPT101B en conséquence).
- Ne **jamais** utiliser CMD, SD0, SD1, SD2, SD3, CLK (flash interne).
- G34, G35, GPIO36 (SP) et GPIO39 (SN) sont **entrées seulement**.
- Tous les canaux utilisés sont sur l'**ADC1** : ils fonctionnent même
  Wi‑Fi actif (l'ADC2 est inutilisable avec le Wi‑Fi — c'est voulu).

## Téléverser (Arduino IDE)

1. Installer le support ESP32 (Gestionnaire de cartes → « esp32 » par Espressif).
2. Ouvrir **`arduino/EMS_ESP32/EMS_ESP32.ino`** (le fichier `config.h` s'ouvre
   automatiquement dans un second onglet, car il est dans le même dossier —
   l'IDE Arduino le compile sans aucun copier-coller).
3. Carte : **ESP32 Dev Module** ; vitesse moniteur : **115200**.
4. Téléverser.

### Si le téléversement échoue

L'erreur d'Arduino IDE — « No serial data received » ou « the selected serial
port does not exist or your board is not connected » — est **trompeuse** : elle
apparaît aussi quand la carte est bien branchée. Le vrai message est visible en
interrogeant la carte avec un esptool récent :

```
Wrong boot mode detected (0x13)! The chip needs to be in download mode.
```

La carte répond, mais démarre sur son firmware au lieu d'attendre un flash : son
circuit d'auto-reset (DTR/RTS) ne tire pas `GPIO0` à LOW. Il faut le forcer :

- Lancer le téléversement, puis **maintenir BOOT** (parfois `IO0`/`FLASH`) dès
  l'apparition de `Connecting........`, jusqu'à `Writing at 0x...`.
- Séquence infaillible si la carte a un bouton **EN**/**RST** : maintenir
  **BOOT** → appuyer/relâcher **EN** → relâcher **BOOT**.

Autres pistes : couper l'alimentation du module relais le temps du flash (son
appel de courant peut perturber l'opération s'il est alimenté par l'ESP32) ; et
en cas d'échec systématique, un condensateur **10 µF entre EN et GND** corrige
définitivement l'auto-reset (défaut classique des clones).

Vérifier que la carte est vue : `Silicon Labs CP210x USB to UART Bridge (COMx)`
dans le Gestionnaire de périphériques. Sinon, installer le pilote CP210x.

## Commandes série (moniteur à 115200 bauds)

| Commande | Effet |
|----------|-------|
| `on 1` / `off 1` | Ligne 1 ON/OFF (passe en mode manuel) |
| `on 2` / `off 2` | Ligne 2 ON/OFF |
| `on 3` / `off 3` | Ligne 3 ON/OFF |
| `all on` / `all off` | Toutes les lignes |
| `auto` | Mode automatique (règles locales ou backend) |
| `manual` | Mode manuel |
| `status` | Affiche l'état complet (JSON) |
| `help` | Liste des commandes |

Toutes les 3 s, le firmware publie une ligne JSON avec le mode, l'état des
relais, et pour chaque ligne : RMS bruts capteurs, tension, courant,
puissance, plus la puissance totale.

## Procédure de mise en service (dans cet ordre)

1. **Relais sans AC** : téléverser, ouvrir le moniteur, tester
   `on 1` → clic du relais CH1, `off 1`, puis lignes 2 et 3, `all on`, `all off`.
2. **Lectures analogiques** : toujours sans AC, vérifier que les
   `vSensorRms`/`iSensorRms` sont proches de 0 (bruit < 0,01 V typique).
3. **Calibration** (avec AC, prudence !) : brancher une seule ligne,
   mesurer la tension réelle au multimètre, puis dans `config.h` :
   `CAL_Vx = tension_reelle / vSensorRms_affiché`. Idem pour le courant
   avec une charge connue : `CAL_Ix = courant_reel / iSensorRms_affiché`.
   Re-téléverser après chaque ajustement.
4. **Connecter ligne par ligne** et vérifier la cohérence des puissances.
5. **Mode automatique** : taper `auto`. Sans Wi‑Fi (`USE_WIFI 0`), les
   règles locales s'appliquent (L3 prioritaire, L1 moyenne, L2 délestée
   en premier ; seuils 80 W/ligne, 120 W total — onduleur 150 W).

## Commande depuis les interfaces web / mobile

Le firmware sait interroger le backend EMS pour recevoir l'état voulu des
3 lignes ; les interfaces (page **Équipements → Contrôle des lignes**)
écrivent cet état. Chaîne complète :

```
Interface (toggle Ligne 1/2/3)  ->  backend (état mémorisé par maison)
                                        ^
                                        | sondage HTTP toutes les ~3 s
                                 ESP32 (mode auto)  ->  relais  ->  charges
```

Mise en service (liaison **automatique**, sans jeton) :

1. Démarrer le backend EMS sur le réseau local (ex. `http://172.20.10.14:8000`).
2. Dans `config.h` : passer `USE_WIFI` à `1`, renseigner `WIFI_SSID` /
   `WIFI_PASSWORD`, et l'IP du serveur dans `BACKEND_DECISION_URL`
   (`http://172.20.10.14:8000/api/ems/decision/`, sans jeton).
3. Re-téléverser. Avec `USE_WIFI 1`, l'ESP32 démarre en mode auto (relais OFF
   jusqu'au premier sondage).
4. Dans l'app, ouvrir **Équipements → Contrôle des lignes** du micro-réseau à
   piloter et actionner une ligne : le nœud se lie automatiquement à ce
   micro-réseau et applique ensuite ses commandes.

> Option avancée : pour figer le nœud sur un micro-réseau précis quel que soit
> le dernier piloté, ajoutez `?token=LE_JETON` à l'URL (jeton renvoyé par
> `GET /api/houses/<id>/relays/`).

Échange réseau :

- POST des mesures en JSON (`{"line1":{...},"line2":{...},"line3":{...}}`) sur
  `BACKEND_DECISION_URL` ;
- réponse texte : `L1=1;L2=0;L3=1` (état voulu, 1 = ligne connectée).

**Comportement de sécurité :**

- au démarrage : tous relais OFF (niveau inactif imposé avant même la
  configuration des pins — pas de claquement au boot) ; sans Wi-Fi, mode
  manuel (série) ; avec Wi-Fi, mode auto ;
- backend injoignable : dernier état conservé ; après 3 échecs consécutifs,
  la ligne non prioritaire (L2) est coupée par précaution ;
- garde-fou local : même une commande reçue ne peut pas activer une ligne que
  les règles de surcharge interdisent (seuils 80 W/ligne, 120 W total) — ce
  garde-fou ne devient effectif qu'une fois les capteurs calibrés.

> Latence : le changement d'un interrupteur dans l'interface est appliqué au
> prochain sondage du nœud (`MEASURE_INTERVAL_MS`, 3 s par défaut ; réduire
> cette valeur pour une réaction plus rapide).

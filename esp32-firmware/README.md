# EMS ESP32 — Firmware « 3 lignes »

Firmware du prototype IoT du système EMS : mesure de tension/courant sur
3 lignes AC et commande de 3 relais, en mode manuel (port série) ou
automatique (règles locales de secours, ou système expert backend via HTTP).

```
esp32-firmware/
├── platformio.ini      # configuration PlatformIO (carte esp32dev)
├── include/
│   └── config.h        # config PlatformIO : pins, calibration, seuils, Wi-Fi
├── src/
│   └── main.cpp        # logique du firmware (PlatformIO)
└── arduino/
    └── EMS_ESP32/      # même firmware, prêt pour l'IDE Arduino
        ├── EMS_ESP32.ino
        └── config.h
```

> **PlatformIO ou Arduino IDE ?** Les deux versions contiennent le même code.
> PlatformIO compile `src/main.cpp` + `include/config.h`. L'IDE Arduino, lui, ne
> lit **que** les fichiers du dossier de croquis : utilisez alors `arduino/EMS_ESP32/`,
> qui contient déjà `config.h` **à côté** du `.ino` (aucun copier-coller). Si vous
> modifiez la configuration, pensez à répercuter le changement dans les deux `config.h`.

## Câblage (NE PAS MODIFIER SANS REVALIDER)

### Relais (module 8 canaux, 3 utilisés)

| GPIO ESP32 | Entrée module | Canal | Ligne |
|-----------|---------------|-------|-------|
| G25 | IN1 | CH1 (COM1/NO1) | Ligne 1 |
| G26 | IN3 | CH3 (COM3/NO3) | Ligne 2 |
| G27 | IN6 | CH6 (COM6/NO6) | Ligne 3 |

Le module est supposé **actif à LOW** (`RELAY_ACTIVE_LOW = true` dans
`config.h`). Si un relais colle à l'envers, passez cette constante à `false`.

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

## Téléverser avec PlatformIO (recommandé)

1. Installer [VS Code](https://code.visualstudio.com/) puis l'extension
   **PlatformIO IDE** (ou en CLI : `pip install platformio`).
2. Ouvrir le dossier `esp32-firmware/` (PlatformIO détecte `platformio.ini`).
3. Brancher l'ESP32 en USB.

```bash
cd esp32-firmware
pio run                # compile
pio run -t upload      # compile + téléverse
pio device monitor     # moniteur série à 115200 bauds
```

Si le port COM n'est pas détecté automatiquement, décommentez
`upload_port`/`monitor_port` dans `platformio.ini` (voir le port dans le
Gestionnaire de périphériques Windows).

> Astuce : si le téléversement échoue avec « Failed to connect », maintenez
> le bouton **BOOT** de la carte pendant les premières secondes de l'upload.

## Alternative : Arduino IDE

1. Installer le support ESP32 (Gestionnaire de cartes → « esp32 » par Espressif).
2. Ouvrir **`arduino/EMS_ESP32/EMS_ESP32.ino`** (le fichier `config.h` s'ouvre
   automatiquement dans un second onglet, car il est dans le même dossier —
   l'IDE Arduino le compile sans aucun copier-coller).
3. Carte : **ESP32 Dev Module** ; vitesse moniteur : **115200**.
4. Téléverser.

> Ne pas ouvrir `src/main.cpp` directement dans l'IDE Arduino : il ne trouverait
> pas `config.h` (rangé dans `include/` pour PlatformIO), d'où les erreurs
> « `RELAY_ACTIVE_LOW` was not declared in this scope ». Utilisez le dossier
> `arduino/EMS_ESP32/`.

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

## Intégration backend (plus tard)

1. Dans `config.h` : `USE_WIFI 1`, renseigner `WIFI_SSID`,
   `WIFI_PASSWORD` et `BACKEND_DECISION_URL`.
2. Le firmware POSTe les mesures en JSON :

```json
{
  "line1": {"voltage": 0.0, "current": 0.0, "power": 0.0},
  "line2": {"voltage": 0.0, "current": 0.0, "power": 0.0},
  "line3": {"voltage": 0.0, "current": 0.0, "power": 0.0}
}
```

3. Réponse attendue (texte brut) : `L1=1;L2=0;L3=1`

**Comportement de sécurité :**

- au démarrage : mode manuel, tous relais OFF (niveau inactif imposé avant
  même la configuration des pins — pas de claquement au boot) ;
- backend injoignable : dernier état conservé ; après 3 échecs consécutifs,
  la ligne non prioritaire (L2) est coupée par précaution ;
- garde-fou local : même une décision backend ne peut pas activer une ligne
  que les règles de surcharge interdisent.

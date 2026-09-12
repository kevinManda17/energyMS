# Prompt pour Claude Code — firmware EMS (deux nœuds ESP32)

> À coller dans Claude Code, à la racine du dépôt de l'application EMS.
> Objectif : un firmware **minimal, lisible et qui marche** pour tout le
> système. N'ajoute rien qui ne soit pas demandé ici.

## Contexte

Écosystème IoT de gestion d'énergie (mémoire de Keven). Le firmware ESP32 a été
retiré ; on repart de zéro. Le système complet tient sur **deux ESP32**, imposé
par le matériel (15 voies analogiques, 6 canaux d'ADC1, et le WiFi qui confisque
l'ADC2) :

- **Nœud PRINCIPAL (AC)** — WiFi : 3 tensions (ZMPT101B) + 3 courants (ZMCT103C)
  + 3 relais. Commande les relais et parle au serveur.
- **Nœud SECONDAIRE (DC)** — sans WiFi : 3 courants (ACS712) + 3 tensions (ponts
  diviseurs) + 3 températures (NTC). Mesure et envoie tout par **UART** au
  principal, qui l'intègre à sa remontée serveur.

Flux HTTP documenté du système (à respecter, pas à réinventer) : `POST
/api/ems/decision/` avec les mesures, réponse **texte** `L1=1;L2=0;L3=1` pour
l'état des relais. Le code MQTT du backend existe mais n'était utilisé par
personne — c'est nous qui ajoutons ici le contrôle des relais par MQTT.

## Ce qu'il faut construire

### Nœud PRINCIPAL
1. **Commande 3 relais par MQTT** (cœur de la demande) :
   - souscrit `ems/<HOUSE_ID>/lines/+/set`, payload `1` | `0` | `toggle` ;
   - publie l'état (retenu) `ems/<HOUSE_ID>/lines/Lx/state` = `1`|`0` ;
   - présence (Last Will, retenu) `ems/<HOUSE_ID>/node/principal/status`.
2. **Télémétrie HTTP** — `POST` périodique (lignes AC **+ bloc DC** reçu par
   UART) vers l'endpoint de décision. Jeton en en-tête `X-Device-Token` (plus de
   requête anonyme). Primitive unique `httpSend(method, url, body)` pour
   POST/GET/PATCH.
3. **Mesure AC** — tension/courant efficaces des 3 lignes.
4. **Réception UART** des mesures DC depuis le secondaire.

### Nœud SECONDAIRE
1. **Mesure DC** — 3 courants ACS712, 3 tensions (ponts), 3 températures NTC.
2. **Envoi UART** de ces 9 valeurs au principal, à cadence fixe.
3. **Pas de WiFi** (c'est ce qui rend l'ADC2 disponible pour les NTC).

## Faits matériels (schéma Version C — ne pas recalculer)

Brochage **PRINCIPAL** (ADC1 uniquement) :

| Ligne | Tension | Courant | Relais (GPIO → entrée) |
|-------|---------|---------|------------------------|
| L1 | GPIO36 | GPIO39 | GPIO25 → IN2 → NO2 |
| L2 | GPIO34 | GPIO35 | GPIO26 → IN3 → NO3 |
| L3 | GPIO32 | GPIO33 | GPIO27 → IN6 → NO6 |

Brochage **SECONDAIRE** (6 voies ADC1, 3 NTC sur ADC2) :

| Grandeur | DC1 | DC2 | DC3 |
|----------|-----|-----|-----|
| Courant ACS712 | GPIO36 (I_PV, 05B) | GPIO39 (I_BAT1, 20A) | GPIO34 (I_BAT2, 20A) |
| Tension pont 100k/15k | GPIO35 (V_PV) | GPIO32 (V_REG) | GPIO33 (V_BAT) |
| Température NTC 10k | GPIO25 (bat.1) | GPIO26 (bat.2) | GPIO27 (panneau) |

- **UART croisé** : secondaire TX2 (GPIO17) → principal RX2 (GPIO16), masse
  commune. Baud 115200. Trame `$DC,i1,i2,i3,v1,v2,v3,t1,t2,t3*CK\n`, CK = XOR
  hex entre `$` et `*` — **format identique des deux côtés**.
- **Ratios confirmés par le schéma** : pont de sortie ACS712 10k/15k (k = 0,600),
  pont de tension DC 100k/15k (k = 0,13043), tirage NTC 10k B3950.
- **Niveau relais paramétrable** `RELAY_ACTIVE_LOW` (défaut 1 = optocoupleur
  actif au niveau bas). Raisonne en « ligne alimentée / coupée ».
- **État relais repos écrit dès le début du `setup()`** (limite le collage au reset).
- ADC : 12 bits, atténuation 11 dB. AC : fenêtre efficace 100 ms. DC : moyenne de
  20 échantillons espacés de 1 ms.

## Contraintes du projet (non négociables)

- **Aucun secret versionné.** `config.h` (versionné) séparé de `secrets.h`
  (**gitignoré**) côté principal ; fournir `secrets.example.h`. Le secondaire
  n'a ni secret ni réseau.
- **Dépendance externe unique : PubSubClient** (principal). Pas de bibliothèque
  JSON : corps HTTP au `snprintf`, réponse et trame UART au parsing de chaîne.
- **Commentaires en français**, style sobre.
- **Ne rien inventer** : vérifier les points ci-dessous dans le dépôt réel.
- Ne pas toucher `apps/fuzzy_engine/core/`. Branche dédiée, pas de merge dans `main`.

## À vérifier dans le dépôt avant d'écrire

1. **Dossier firmware** (l'audit mentionne `esp32-firmware/arduino/…`). Créer
   `EMS_ESP32_Principal/` et `EMS_ESP32_Secondaire/` (nom de dossier = nom du `.ino`).
2. **Route + serializer** de `EmsDecisionView` (`apps/devices`) : confirmer
   `/api/ems/decision/` et **les champs exacts** attendus dans le POST, puis
   aligner le `snprintf` (lignes AC **et** bloc DC : i_pv/i_bat1/i_bat2,
   v_pv/v_reg/v_bat, t_bat1/t_bat2/t_pv). Confirmer aussi le format de réponse.
   Vérifier que la sémantique DC1/DC2/DC3 (PV / batterie 1 / batterie 2)
   correspond bien au câblage réel.
3. **Jeton d'appareil** : comment il est vérifié côté backend et l'en-tête attendu.
4. **MQTT** : lire `apps/mqtt_handler/` et `mqtt/mosquitto.conf`. Le contrôle des
   relais par MQTT est nouveau — si le backend doit s'abonner à
   `ems/<house>/lines/+/set` ou publier dessus, **signale-le comme un petit ajout
   backend séparé** (ne pas l'implémenter dans ce jalon sans accord). Pour la
   démo, la commande est publiée à la main (`mosquitto_pub`) ou par le frontend.

## Point de départ

Fichiers déjà rédigés et fournis : `EMS_ESP32_Principal.ino`, `config.h`,
`secrets.example.h`, `EMS_ESP32_Secondaire.ino`, `config_secondaire.h`,
`README_FIRMWARE.md`. Pars de ceux-là ; **ajuste uniquement** le corps JSON du
POST, les chemins/topics et la sémantique DC aux valeurs réelles du dépôt.
Ajoute `secrets.h` au `.gitignore`.

## Critère de réussite

Après flash : `mosquitto_pub -t ems/1/lines/L1/set -m 1` allume la lampe L1,
`-m 0` l'éteint, l'état repart sur `.../state`. Le secondaire flashé, le moniteur
série du principal affiche les trames DC reçues et le POST indique `(DC frais)`.
Rien de plus pour ce jalon.

## À concevoir ensuite (NE PAS improviser)

- **Fil d'alarme matériel** entre les deux nœuds : ouverture immédiate de L2/L3
  sur T > 55 °C, V_BAT < 10,5 V pendant 60 s, ou saturation capteur. Seuils
  câblés en dur, jamais commandés à distance. C'est une **sécurité** : confirmer
  GPIO et topologie (comparateur matériel, ou GPIO piloté par le secondaire et
  lu en interruption par le principal) avant d'écrire du code.
- Voie de référence **V5_MON** (ratiométrie des ACS712) si elle est ajoutée au
  montage : elle ramène l'erreur courant DC de ±3–6 % à ±0,5 %.

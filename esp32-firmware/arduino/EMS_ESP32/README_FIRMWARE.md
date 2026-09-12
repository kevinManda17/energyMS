# Firmware EMS — deux nœuds ESP32

Le système complet tient sur **deux ESP32**, imposé par le matériel : 15 voies
analogiques pour 6 canaux d'ADC1, et le WiFi qui confisque l'ADC2.

| Nœud | Mesure | Réseau | Rôle |
|------|--------|--------|------|
| **PRINCIPAL** (AC) | 3 tensions ZMPT101B + 3 courants ZMCT103C | WiFi + MQTT + HTTP | commande les 3 relais, parle au serveur |
| **SECONDAIRE** (DC) | 3 courants ACS712 + 3 tensions (ponts) + 3 NTC | **aucun** | mesure et envoie tout par UART au principal |

Le secondaire n'a pas de WiFi : c'est **ce qui libère l'ADC2** pour les NTC. Il
envoie ses 9 mesures par UART ; le principal les intègre à son POST vers le
backend — donc vers le système expert.

## Brochage (schéma Version C)

**Nœud PRINCIPAL — ADC1 uniquement**

| Ligne | Tension (ZMPT) | Courant (ZMCT) | Relais (GPIO → entrée) |
|-------|----------------|----------------|------------------------|
| L1    | GPIO36         | GPIO39         | GPIO25 → IN2 → NO2     |
| L2    | GPIO34         | GPIO35         | GPIO26 → IN3 → NO3     |
| L3    | GPIO32         | GPIO33         | GPIO27 → IN6 → NO6     |

**Nœud SECONDAIRE — 6 voies ADC1, 3 voies NTC sur ADC2**

| Grandeur | DC1 | DC2 | DC3 |
|----------|-----|-----|-----|
| Courant (ACS712) | GPIO36 (I_PV, 05B) | GPIO39 (I_BAT1, 20A) | GPIO34 (I_BAT2, 20A) |
| Tension (pont 100k/15k) | GPIO35 (V_PV) | GPIO32 (V_REG) | GPIO33 (V_BAT) |
| Température (NTC 10k) | GPIO25 (bat. 1) | GPIO26 (bat. 2) | GPIO27 (panneau) |

**Liaison UART entre les deux (croisée)**

```
Secondaire GPIO17 (TX2) ───────► GPIO16 (RX2) Principal
Secondaire GPIO16 (RX2) ◄─────── GPIO17 (TX2) Principal   (inutilisé ce jalon)
GND ─────────────────────────────── GND        (masse commune obligatoire)
```

## Préparer

1. Deux dossiers de sketch :
   - `EMS_ESP32_Principal/`  →  `EMS_ESP32_Principal.ino`, `config.h`, `secrets.h`
   - `EMS_ESP32_Secondaire/` →  `EMS_ESP32_Secondaire.ino`, `config_secondaire.h`
2. Côté principal : copier `secrets.example.h` → **`secrets.h`** et remplir
   (WiFi, `HOUSE_ID`, `DEVICE_TOKEN`, IP backend, IP broker).
3. Bibliothèque (principal seulement) : **PubSubClient** (Nick O'Leary).
   Le secondaire n'a aucune dépendance externe.
4. Carte : **ESP32 Dev Module**. Moniteur série : **115200**.

## Tester

**1 — Commande des relais par MQTT** (`HOUSE_ID = 1`) :

```
mosquitto_pub -h <IP_BROKER> -t ems/1/lines/L1/set -m 1        # allume
mosquitto_pub -h <IP_BROKER> -t ems/1/lines/L1/set -m 0        # éteint
mosquitto_pub -h <IP_BROKER> -t ems/1/lines/L1/set -m toggle   # bascule
mosquitto_sub -h <IP_BROKER> -t 'ems/1/lines/+/state' -t 'ems/1/node/principal/status' -v
```

La lampe doit réagir tout de suite, l'état repart sur `ems/1/lines/Lx/state`.

**2 — Chaîne DC** : flasher le secondaire ; sur le moniteur série du principal,
les trames DC reçues s'affichent (`[UART] DC : ...`). Même sans capteurs
branchés, la plomberie UART se valide (valeurs bruitées, mais trames correctes).
Le POST du principal montre alors `(DC frais)`.

## Le piège à connaître

Si une lampe fait **l'inverse** de la commande, bascule `RELAY_ACTIVE_LOW` dans
`config.h` (1 ↔ 0) et reflashe. Seul réglage qui dépend du modèle de module.

## Réglages utiles (`config.h` du principal)

- `HTTP_TELEMETRY_ENABLED` — POST périodique (AC + DC). Mettre `0` pour tester
  MQTT seul.
- `APPLY_SERVER_RELAY_DECISION` — `0` : la réponse HTTP `L1=1;L2=0;L3=1` ne
  touche pas aux relais (contrôle MQTT propre). `1` : comportement piloté par le
  serveur, comme avant.

## À étalonner (aucune valeur mesurée n'est fiable avant ça)

- **AC** : `V_SCALE`, `I_SCALE` (`config.h`). Courant non fiable sous ~0,25 A
  (plancher du ZMCT103C).
- **Courant DC** : `ACS_VZERO_MV` par voie (lecture à courant nul). La dérive du
  rail 5 V est l'erreur dominante.
- **Tension DC** : `VDC_SCALE` par voie (étalonnage à un point au multimètre).
- **NTC** : le montage supposé est 3,3V—[10k]—ADC—[NTC]—GND ; à confirmer sur la
  carte. En dessous de ~+3 °C la voie sature (renvoie −99).

## Non implémenté volontairement (à concevoir ensuite)

Le **fil d'alarme matériel** entre les deux nœuds (ouverture immédiate de L2/L3
sur T > 55 °C, V_BAT < 10,5 V pendant 60 s, ou saturation d'un capteur), câblé
en dur et jamais commandé à distance. C'est une sécurité : son GPIO et sa
topologie doivent être confirmés avant d'écrire quoi que ce soit — on ne devine
pas un interverrouillage de sécurité.

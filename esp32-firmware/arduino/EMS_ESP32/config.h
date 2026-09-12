#pragma once
// ============================================================================
//  EMS IoT — Nœud PRINCIPAL (AC) — Configuration NON secrète
//  ESP32 WROOM-32 · 3 ZMPT101B + 3 ZMCT103C + 3 relais · WiFi + MQTT + HTTP
//
//  Les identifiants (WiFi, jeton d'appareil, broker) vivent dans secrets.h,
//  qui N'EST PAS versionné. Copier secrets.example.h -> secrets.h.
// ============================================================================

// ---------------------------------------------------------------------------
//  Brochage — d'après le schéma électronique (figure A.2, Version C)
//  ADC1 UNIQUEMENT : sur ce nœud le pilote WiFi s'approprie l'ADC2.
//  Les 6 canaux d'ADC1 sont donc exactement pleins.
// ---------------------------------------------------------------------------
// Tension alternative (ZMPT101B) — sortie centrée sur ~Vcc/2
#define PIN_V_L1   36   // GPIO36 (ADC1_CH0) — tension ligne 1
#define PIN_V_L2   34   // GPIO34 (ADC1_CH6) — tension ligne 2
#define PIN_V_L3   32   // GPIO32 (ADC1_CH4) — tension ligne 3
// Courant alternatif (ZMCT103C 1000:1)
#define PIN_I_L1   39   // GPIO39 (ADC1_CH3) — courant ligne 1
#define PIN_I_L2   35   // GPIO35 (ADC1_CH7) — courant ligne 2
#define PIN_I_L3   33   // GPIO33 (ADC1_CH5) — courant ligne 3

// Commande du module relais 8 canaux (on n'en utilise que 3)
// GPIO -> entrée du module -> contact NO -> ligne électrique
#define PIN_RELAY_L1  25   // GPIO25 -> IN2 -> NO2 -> Ligne 1 (lampe 20 W)
#define PIN_RELAY_L2  26   // GPIO26 -> IN3 -> NO3 -> Ligne 2 (lampe 10 W + prise)
#define PIN_RELAY_L3  27   // GPIO27 -> IN6 -> NO6 -> Ligne 3 (lampe 10 W + prise)
//  ⚠ Vérifier le câblage réel IN2/IN3/IN6 : une inversion de fil se corrige ici.

// ---------------------------------------------------------------------------
//  Niveau logique des relais — À CONFIRMER SUR LE MODULE
//    Module optocoupleur du commerce  : ACTIF AU NIVEAU BAS  -> laisser 1
//    Variante MOSFET 2N7000 (note HW)  : ACTIF AU NIVEAU HAUT -> mettre 0
//  Test : commander une ligne à OFF ; si la lampe s'allume, inverser ce 0/1.
// ---------------------------------------------------------------------------
#define RELAY_ACTIVE_LOW  1

// ---------------------------------------------------------------------------
//  Acquisition ADC (voies AC)
// ---------------------------------------------------------------------------
#define ADC_WINDOW_MS   100   // fenêtre efficace : 100 ms = 5 périodes à 50 Hz

// Étalonnage — À MESURER (cf. claude/conception-materielle-decisions.md).
//   V_SCALE : volts efficaces secteur par mV efficace lu (dépend du pot ZMPT).
//   I_SCALE : ampères efficaces par mV efficace lu (dépend de la charge du ZMCT).
//   Valeurs indicatives : à remplacer par un étalonnage à un point PAR voie.
//   Rappel : le courant n'est pas fiable sous ~0,25 A (plancher du ZMCT103C).
static const float V_SCALE[3] = { 0.406f, 0.406f, 0.406f };
static const float I_SCALE[3] = { 0.010f, 0.010f, 0.010f };

// ---------------------------------------------------------------------------
//  Liaison UART vers le nœud secondaire (réception des mesures DC)
//  Doit être identique côté secondaire (baud + format de trame).
// ---------------------------------------------------------------------------
#define UART_BAUD    115200
#define UART_RX_PIN  16       // GPIO16 (RX2) <- TX2 du nœud secondaire
#define UART_TX_PIN  17       // GPIO17 (TX2) -> RX2 du secondaire (inutilisé ce jalon)
#define DC_STALE_MS  15000    // au-delà, les mesures DC sont marquées "périmées"

// ---------------------------------------------------------------------------
//  Liaison HTTP (télémétrie AC+DC + décision serveur — flux existant)
// ---------------------------------------------------------------------------
#define HTTP_TELEMETRY_ENABLED       1        // POST périodique des mesures
#define APPLY_SERVER_RELAY_DECISION  0        // 1 = la réponse backend pilote aussi les relais
#define POST_INTERVAL_MS             10000    // période d'envoi (ms)
#define BACKEND_DECISION_PATH        "/api/ems/decision/"
//  Réponse attendue du backend, format texte : "L1=1;L2=0;L3=1"

// ---------------------------------------------------------------------------
//  Liaison MQTT (commande des relais — c'est le plan de contrôle)
//    Souscription : ems/<HOUSE_ID>/lines/+/set     payload "1" | "0" | "toggle"
//    Publication  : ems/<HOUSE_ID>/lines/Lx/state  payload "1" | "0"   (retenu)
//    Présence     : ems/<HOUSE_ID>/node/principal/status  "online"/"offline"
// ---------------------------------------------------------------------------
#define MQTT_TOPIC_PREFIX   "ems"

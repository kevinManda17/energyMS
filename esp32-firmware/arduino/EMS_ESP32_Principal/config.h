#pragma once
// ============================================================================
//  EMS IoT — Nœud PRINCIPAL (AC) — Configuration NON secrète
//  ESP32 WROOM-32 · 3 ZMPT101B + 3 ZMCT103C + 3 relais · WiFi + HTTP
//  Les identifiants vivent dans secrets.h (NON versionné).
// ============================================================================

// ---------------------------------------------------------------------------
//  Brochage — schéma Version C. ADC1 uniquement (le WiFi occupe l'ADC2).
// ---------------------------------------------------------------------------
#define PIN_V_L1   36   // GPIO36 — tension ligne 1 (ZMPT101B)
#define PIN_V_L2   34   // GPIO34 — tension ligne 2
#define PIN_V_L3   32   // GPIO32 — tension ligne 3
#define PIN_I_L1   39   // GPIO39 — courant ligne 1 (ZMCT103C)
#define PIN_I_L2   35   // GPIO35 — courant ligne 2
#define PIN_I_L3   33   // GPIO33 — courant ligne 3

#define PIN_RELAY_L1  25   // GPIO25 -> IN2 -> NO2 -> Ligne 1
#define PIN_RELAY_L2  26   // GPIO26 -> IN3 -> NO3 -> Ligne 2
#define PIN_RELAY_L3  27   // GPIO27 -> IN6 -> NO6 -> Ligne 3

// Niveau relais — À CONFIRMER : optocoupleur = actif bas -> 1 ; MOSFET -> 0.
// Si une lampe fait l'inverse de la commande, inverser ce 0/1 et reflasher.
#define RELAY_ACTIVE_LOW  1

// ---------------------------------------------------------------------------
//  Acquisition AC
// ---------------------------------------------------------------------------
#define ADC_WINDOW_MS   100   // fenêtre efficace : 100 ms = 5 périodes à 50 Hz

// Étalonnage — À MESURER (un point par voie). Valeurs indicatives.
static const float V_SCALE[3] = { 0.406f, 0.406f, 0.406f };  // Vrms secteur / mV
static const float I_SCALE[3] = { 0.010f, 0.010f, 0.010f };  // A / mV

// ---------------------------------------------------------------------------
//  Liaison UART vers le nœud secondaire (mesures DC). Identique côté secondaire.
// ---------------------------------------------------------------------------
#define UART_BAUD    115200
#define UART_RX_PIN  16       // GPIO16 (RX2) <- TX2 du secondaire
#define UART_TX_PIN  17       // GPIO17 (TX2) -> RX2 du secondaire (inutilisé ici)
#define DC_STALE_MS  15000    // au-delà, les mesures DC sont "périmées"

// ---------------------------------------------------------------------------
//  Liaison HTTP (télémétrie AC+DC + décision serveur)
// ---------------------------------------------------------------------------
#define HTTP_TELEMETRY_ENABLED       1
// Le backend renvoie "L1=..;L2=..;L3=.." ; l'ESP32 l'applique. C'est ainsi que
// les lampes suivent l'app (PATCH /api/houses/<id>/relays/). Laisser à 1.
#define APPLY_SERVER_RELAY_DECISION  1
// Cadence de sondage : 3 s, la cadence nominale du systeme. Le backend, lui,
// n'archive les mesures et n'evalue le systeme expert que toutes les 30 s
// (MEASUREMENT_STORE_INTERVAL_S) : sonder plus vite ne sature donc pas la base,
// cela rend seulement l'application plus reactive -- une commande passee dans
// l'interface atteint les relais en 3 s au lieu de 10.
#define POST_INTERVAL_MS             3000
#define BACKEND_DECISION_PATH        "/api/ems/decision/"

#pragma once
// ============================================================================
//  EMS IoT — Nœud SECONDAIRE (DC) — Configuration
//  ESP32 WROOM-32 · 3 ACS712 + 3 ponts DC + 3 NTC · SANS WiFi
//
//  Ce nœud n'a ni réseau ni secret : le WiFi est volontairement coupé, ce qui
//  libère l'ADC2 pour les 3 voies NTC. Il mesure et envoie tout par UART au
//  nœud principal, qui parle au serveur.
// ============================================================================

// ---------------------------------------------------------------------------
//  Brochage (schéma Version C) — 6 voies sur ADC1, 3 voies NTC sur ADC2.
// ---------------------------------------------------------------------------
// Courants DC (ACS712, sortie ramenée par pont 10k/15k, k = 0,600)
#define PIN_I_DC1  36   // GPIO36 — I_PV   (ACS712-05B)
#define PIN_I_DC2  39   // GPIO39 — I_BAT1 (ACS712-20A)
#define PIN_I_DC3  34   // GPIO34 — I_BAT2 (ACS712-20A)
// Tensions DC (pont diviseur 100k/15k, k = 0,13043)
#define PIN_V_DC1  35   // GPIO35 — V_PV
#define PIN_V_DC2  32   // GPIO32 — V_REG
#define PIN_V_DC3  33   // GPIO33 — V_BAT
// Températures (NTC 10k B3950 + tirage 10k) — sur ADC2 (dispo car pas de WiFi)
#define PIN_T_1    25   // GPIO25 — NTC batterie 1
#define PIN_T_2    26   // GPIO26 — NTC batterie 2
#define PIN_T_3    27   // GPIO27 — NTC panneau solaire

// ---------------------------------------------------------------------------
//  Liaison UART vers le nœud principal — DOIT matcher l'autre config.
// ---------------------------------------------------------------------------
#define UART_BAUD          115200
#define UART_RX_PIN        16     // GPIO16 (RX2) — inutilisé (envoi seul ce jalon)
#define UART_TX_PIN        17     // GPIO17 (TX2) -> RX2 du nœud principal
#define SEND_INTERVAL_MS   2000   // cadence d'envoi des mesures

// ---------------------------------------------------------------------------
//  Acquisition — voies continues : moyenne de 20 échantillons espacés de 1 ms
//  (= 2 périodes de l'ondulation onduleur à 100 Hz).
// ---------------------------------------------------------------------------
#define DC_SAMPLES   20
#define DC_GAP_MS    1

// ---------------------------------------------------------------------------
//  Étalonnage courant (ACS712)
//    I = (V_adc - V_zero) / k_div / sensibilité
//    k_div = pont de sortie 10k/15k = 0,600 (schéma Version C)
//    sensibilité : 05B = 0,185 V/A ; 20A = 0,100 V/A
//    V_zero_adc : lecture à courant nul, en mV. Nominal 2,5 V × 0,600 = 1500 mV.
//    À ÉTALONNER par voie : la dérive du rail 5 V est l'erreur dominante (doc HW).
// ---------------------------------------------------------------------------
#define ACS_KDIV           0.600f
static const float ACS_SENS[3]     = { 0.185f, 0.100f, 0.100f };   // V/A
static const float ACS_VZERO_MV[3] = { 1500.0f, 1500.0f, 1500.0f };

// ---------------------------------------------------------------------------
//  Étalonnage tension DC (pont 100k/15k)
//    V_bus = V_adc(mV) × VDC_SCALE. Nominal 1/(1000×0,13043) = 0,007667 V/mV.
//    Étalonnage à un point par voie (absorbe la tolérance des résistances).
// ---------------------------------------------------------------------------
static const float VDC_SCALE[3] = { 0.007667f, 0.007667f, 0.007667f };

// ---------------------------------------------------------------------------
//  NTC (équation Beta)
//    Montage : 3,3V — [tirage 10k] — ADC — [NTC] — GND (Vadc chute quand chaud).
//    R_ntc = R_FIXED × Vadc/(VSUP - Vadc) ; 1/T = 1/T0 + ln(R/R0)/BETA.
//    En dessous de ~+3 °C la voie sature (hors plage ADC) -> renvoie NTC_INVALID.
// ---------------------------------------------------------------------------
#define NTC_VSUP     3.3f
#define NTC_RFIXED   10000.0f
#define NTC_R0       10000.0f
#define NTC_T0_K     298.15f
#define NTC_BETA     3950.0f
#define NTC_INVALID  -99.0f

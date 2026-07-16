/*
 * config.h — Toute la configuration modifiable du firmware EMS ESP32.
 *
 * ⚠ NE PAS MODIFIER LE MAPPING DES PINS sans revalider le câblage physique.
 *
 * Mapping physique confirmé :
 *   Relais (module 8 canaux, seuls 3 utilisés) :
 *     G25 -> IN1 -> CH1 -> Ligne 1
 *     G26 -> IN3 -> CH3 -> Ligne 2
 *     G27 -> IN6 -> CH6 -> Ligne 3
 *   Capteurs analogiques (sorties <= 3.3 V impératif) :
 *     ZMPT101B-1 OUT -> G34   | ZMCT103C-1 OUT -> G35
 *     ZMPT101B-2 OUT -> G32   | ZMCT103C-2 OUT -> G33
 *     ZMPT101B-3 OUT -> SP/G36| ZMCT103C-3 OUT -> SN/G39
 *
 *   Interdits : CMD, SD0, SD1, SD2, SD3, CLK (flash SPI interne).
 *   G34, G35, G36 (SP) et G39 (SN) sont des entrées seulement — parfait
 *   pour l'ADC, jamais utilisables en sortie.
 *   Tous ces canaux sont sur l'ADC1 : ils restent fonctionnels quand le
 *   Wi-Fi est actif (l'ADC2, lui, est réquisitionné par le Wi-Fi).
 */

#pragma once

#include <Arduino.h>

/* ==================== WIFI / BACKEND ==================== */
/* Laisser USE_WIFI à 0 pour les premiers tests sur table.
 * Passer à 1 quand le backend expert est joignable. */
#define USE_WIFI 1

// constexpr const char* WIFI_SSID     = "iphone de IRON MANDA";
// constexpr const char* WIFI_PASSWORD = "iron@17kev_@09electronics12a12K17";

constexpr const char* WIFI_SSID     = "itel A50C";
constexpr const char* WIFI_PASSWORD = "";



/* Le backend reçoit les mesures en JSON (POST) et répond en texte simple :
 *   L1=1;L2=0;L3=1                                                       */
// constexpr const char* BACKEND_DECISION_URL =
//     "http://172.20.10.14:8000/api/ems/decision/";

//constexpr const char* BACKEND_DECISION_URL =
//    "http://192.168.203.117:8000/api/ems/decision/";

constexpr const char* BACKEND_DECISION_URL =
    "http://192.168.188.117:8000/api/ems/decision/";

    //  192.168.203.117

constexpr uint16_t HTTP_TIMEOUT_MS = 3000;

/* Après ce nombre d'échecs backend consécutifs en mode auto, la ligne
 * non prioritaire (L2) est coupée par précaution ; L1/L3 gardent leur
 * dernier état connu. */
constexpr uint8_t BACKEND_MAX_FAILURES = 3;

/* ==================== RELAIS ==================== */
/* Seul endroit qui traduit "ligne active" en niveau electrique : partout
 * ailleurs (UI, backend, protocole L1=1, clampDecision) true = ligne sous
 * tension. Ne jamais compenser une inversion cote interface : la protection
 * surcharge ecrit d.lX = false pour COUPER, et s'inverserait aussi. */
constexpr bool RELAY_ACTIVE_LOW = false;

constexpr uint8_t RELAY_L1_PIN = 25;  // G25 -> IN1
constexpr uint8_t RELAY_L2_PIN = 26;  // G26 -> IN3
constexpr uint8_t RELAY_L3_PIN = 27;  // G27 -> IN6

/* ==================== CAPTEURS ==================== */
constexpr uint8_t PIN_V1 = 34;  // ZMPT101B-1 (G34, entrée seule, ADC1)
constexpr uint8_t PIN_I1 = 35;  // ZMCT103C-1 (G35, entrée seule, ADC1)
constexpr uint8_t PIN_V2 = 32;  // ZMPT101B-2 (G32, ADC1)
constexpr uint8_t PIN_I2 = 33;  // ZMCT103C-2 (G33, ADC1)
constexpr uint8_t PIN_V3 = 36;  // ZMPT101B-3 (SP = GPIO36, entrée seule)
constexpr uint8_t PIN_I3 = 39;  // ZMCT103C-3 (SN = GPIO39, entrée seule)

constexpr float ADC_REF_V = 3.3f;
constexpr int   ADC_MAX   = 4095;

/* 600 échantillons × 500 µs = 300 ms par canal, soit ~15 périodes à 50 Hz :
 * suffisant pour un RMS stable. */
constexpr int RMS_SAMPLES      = 600;
constexpr int SAMPLE_DELAY_US  = 500;

/* ==================== CALIBRATION ==================== */
/* 1.0 au départ : on lit alors le RMS brut (en volts) côté sortie capteur.
 * Après mesure de référence au multimètre :
 *   CAL_Vx = tension_reelle_AC  / tension_rms_sortie_ZMPT101B
 *   CAL_Ix = courant_reel_AC    / tension_rms_sortie_ZMCT103C            */
constexpr float CAL_V1 = 1.0f;
constexpr float CAL_I1 = 1.0f;
constexpr float CAL_V2 = 1.0f;
constexpr float CAL_I2 = 1.0f;
constexpr float CAL_V3 = 1.0f;
constexpr float CAL_I3 = 1.0f;

/* ==================== SEUILS DE SECURITE ==================== */
/* Onduleur 150 W -> marge de sécurité. Le vrai système expert est côté
 * backend ; ces règles locales servent de secours et de garde-fou. */
constexpr float MAX_TOTAL_POWER_W = 120.0f;
constexpr float MAX_LINE_POWER_W  = 80.0f;

/* ==================== CADENCE ==================== */
constexpr unsigned long MEASURE_INTERVAL_MS = 3000;

/*
 * config.h — Toute la configuration modifiable du firmware EMS ESP32.
 *
 * ⚠ NE PAS MODIFIER LE MAPPING DES PINS sans revalider le câblage physique.
 *
 * Mapping physique confirmé :
 *   Relais (module 8 canaux, seuls 3 utilisés) :
 *     G25 -> IN2 -> CH2 (COM2/NO2) -> Ligne 1
 *     G26 -> IN3 -> CH3 (COM3/NO3) -> Ligne 2
 *     G27 -> IN6 -> CH6 (COM6/NO6) -> Ligne 3
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

/* Ce fichier est versionne et pousse sur GitHub : ne jamais y ecrire un mot de
 * passe reel, meme en commentaire. Un mot de passe pousse ici est publie, et le
 * retirer ensuite ne l'efface pas de l'historique — il faut le CHANGER sur la
 * box / le telephone. Reseau ouvert (hotspot sans mot de passe) : chaine vide. */
// constexpr const char* WIFI_SSID     = "iphone de IRON MANDA";
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

/* Valeur = GPIO de l'ESP32 ; le canal du module (IN./COM./NO.) ne depend que
 * du cablage et n'a pas a etre declare ici. */
constexpr uint8_t RELAY_L1_PIN = 25;  // G25 -> IN2 (CH2 : COM2/NO2)
constexpr uint8_t RELAY_L2_PIN = 26;  // G26 -> IN3 (CH3 : COM3/NO3)
constexpr uint8_t RELAY_L3_PIN = 27;  // G27 -> IN6 (CH6 : COM6/NO6)

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
/* Le firmware calcule le RMS *de la sortie du capteur* (volts ADC), pas la
 * grandeur physique ; CAL_Vx est le facteur d'échelle appliqué par ligne.
 * Chaque ZMPT101B a son propre potentiomètre : les 3 lignes n'ont donc PAS le
 * même facteur (avec 709,7 commun, on a relevé 269 V et 252 V au lieu de 220).
 *
 * MÉTHODE ITÉRATIVE (la plus simple — pas besoin de lire le RMS brut) :
 *   nouveau_CAL_Vx = CAL_Vx_actuel × (tension_vraie / tension_affichée)
 * Exemple réel, depuis CAL = 709,7 :
 *   ligne affichant 269 V -> 709,7 × 220/269 ≈ 580
 *   ligne affichant 252 V -> 709,7 × 220/252 ≈ 620
 * Répéter une fois si besoin (ça converge vite). « tension_vraie » = la valeur
 * au multimètre sur CETTE ligne (≈220 V ici ; utiliser 230 si c'est le secteur
 * réel mesuré). Ne PAS retoucher le potentiomètre après coup (invalide le CAL).
 *
 * ⚠ Les valeurs ci-dessous supposent : L1 lisait 269, L2 lisait 252, L3 non
 *   mesurée (moyenne). À vérifier/permuter selon la ligne réellement relevée.
 */
constexpr float CAL_V1 = 580.0f;   // affinée depuis 269 V affichés
constexpr float CAL_V2 = 620.0f;   // affinée depuis 252 V affichés
constexpr float CAL_V3 = 600.0f;   // non mesurée : moyenne, à affiner

/* COURANT — non calibré (aucune mesure de référence fournie) : laisser à 1.0
 * jusqu'à mesurer, avec une charge connue, CAL_Ix = courant_réel / iSensorRms. */
constexpr float CAL_I1 = 1.0f;
constexpr float CAL_I2 = 1.0f;
constexpr float CAL_I3 = 1.0f;

/* ==================== SEUILS DE SECURITE ==================== */
/* Onduleur 150 W -> marge de sécurité. Le vrai système expert est côté
 * backend ; ces règles locales servent de secours et de garde-fou. */
constexpr float MAX_TOTAL_POWER_W = 120.0f;
constexpr float MAX_LINE_POWER_W  = 80.0f;

/* ==================== CADENCE ==================== */
constexpr unsigned long MEASURE_INTERVAL_MS = 3000;

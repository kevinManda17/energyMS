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



/* Adresse du backend, en trois constantes séparées : seul BACKEND_HOST change
 * quand le PC change de réseau. Jamais "localhost" ici — sur l'ESP32, localhost
 * désigne l'ESP32 lui-même, pas le PC.
 *
 * Le backend reçoit les mesures en JSON (POST) et répond en texte simple :
 *   L1=1;L2=0;L3=1
 *
 * Historique des adresses (réseaux précédents) : 172.20.10.14, 192.168.203.117,
 * 192.168.188.117. Pour connaître l'adresse courante du PC :
 *   python scripts/configure_lan.py
 *
 * ÉVOLUTION PRÉVUE (non implémentée) : rendre l'hôte modifiable sans recompiler,
 * via une commande série (`host 192.168.x.y`) stockée en NVS Preferences, ou par
 * découverte mDNS. Aujourd'hui, changer de réseau impose un téléversement.      */
/* >>> SEULE LIGNE À MODIFIER quand le PC change de réseau <<< */
#define BACKEND_HOST_STR "192.168.84.117"
#define BACKEND_PORT_NUM 8000
#define BACKEND_PATH_STR "/api/ems/decision/"

/* Tout le reste est dérivé : rien d'autre à toucher. */
#define _EMS_STR2(x) #x
#define _EMS_STR(x) _EMS_STR2(x)

constexpr const char* BACKEND_HOST = BACKEND_HOST_STR;
constexpr uint16_t    BACKEND_PORT = BACKEND_PORT_NUM;
constexpr const char* BACKEND_PATH = BACKEND_PATH_STR;

constexpr const char* BACKEND_DECISION_URL =
    "http://" BACKEND_HOST_STR ":" _EMS_STR(BACKEND_PORT_NUM) BACKEND_PATH_STR;

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
/* PRINCIPE — le seul mécanisme de calibration du firmware est un coefficient
 * multiplicatif par ligne. Aucune tension n'est plafonnée, arrondie ou forcée
 * vers une valeur « plausible » : les fluctuations réelles doivent apparaître.
 * Si L1 est à 217 V, L2 à 224 V et L3 à 210 V, le système doit afficher
 * 217 / 224 / 210 — et non ramener les trois à une même valeur.
 *
 *     Vrms_calibrée = Vrms_brute × CAL_Vx
 *     Irms_calibré  = Irms_brut  × CAL_Ix
 *
 * Chaque ZMPT101B / ZMCT103C a son propre potentiomètre : les trois lignes ont
 * donc des coefficients DIFFÉRENTS. Une valeur commune est forcément fausse sur
 * au moins deux lignes.
 *
 * MÉTHODE (tension), à refaire pour CHAQUE ligne :
 *   1. mesurer la tension réelle de la ligne au multimètre (ex. 217 V) ;
 *   2. lire la tension affichée par l'ESP32 pour cette même ligne ;
 *   3. nouveau_CAL_Vx = CAL_Vx_actuel × (tension_multimètre / tension_affichée) ;
 *   4. téléverser, puis vérifier ; répéter une fois si l'écart persiste.
 *   Ne PAS retoucher le potentiomètre après calibration (cela l'invalide).
 *
 * MÉTHODE (courant), avec une charge connue :
 *   1. brancher une charge de puissance connue (ex. lampe 20 W à ~220 V) ;
 *   2. courant attendu ≈ P / U (20 / 220 ≈ 0,09 A) ;
 *   3. nouveau_CAL_Ix = CAL_Ix_actuel × (courant_attendu / courant_affiché).
 *
 * ÉTAT : coefficients NON calibrés (1.0 = on lit le RMS brut du capteur, en
 * volts ADC). Les valeurs affichées ne seront donc pas des volts/ampères réels
 * tant que la procédure ci-dessus n'a pas été faite ligne par ligne. C'est
 * volontaire : mieux vaut une valeur brute assumée qu'un chiffre inventé.
 */
constexpr float CAL_V1 = 1.0f;   // à calibrer : U_multimètre / U_affichée (ligne 1)
constexpr float CAL_V2 = 1.0f;   // à calibrer : U_multimètre / U_affichée (ligne 2)
constexpr float CAL_V3 = 1.0f;   // à calibrer : U_multimètre / U_affichée (ligne 3)

constexpr float CAL_I1 = 1.0f;   // à calibrer : I_attendu / I_affiché (ligne 1)
constexpr float CAL_I2 = 1.0f;   // à calibrer : I_attendu / I_affiché (ligne 2)
constexpr float CAL_I3 = 1.0f;   // à calibrer : I_attendu / I_affiché (ligne 3)

/* ==================== SEUILS DE SECURITE ==================== */
/* Onduleur 150 W -> marge de sécurité. Le vrai système expert est côté
 * backend ; ces règles locales servent de secours et de garde-fou. */
constexpr float MAX_TOTAL_POWER_W = 120.0f;
constexpr float MAX_LINE_POWER_W  = 80.0f;

/* ==================== CADENCE ==================== */
constexpr unsigned long MEASURE_INTERVAL_MS = 3000;

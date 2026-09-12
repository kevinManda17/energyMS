#pragma once
// ============================================================================
//  MODÈLE — copier ce fichier en "secrets.h" et remplir les valeurs.
//  secrets.h NE DOIT PAS être versionné (l'ajouter au .gitignore).
// ============================================================================

// --- WiFi -------------------------------------------------------------------
#define WIFI_SSID      "MON_WIFI"
#define WIFI_PASSWORD  "MON_MOT_DE_PASSE"

// --- Identité du nœud (topics MQTT + API) -----------------------------------
#define HOUSE_ID       "1"          // identifiant de la maison / micro-réseau

// --- Authentification HTTP (en-tête X-Device-Token) -------------------------
//  Correctif de sécurité : l'endpoint ne doit plus accepter les requêtes
//  anonymes. Coller ici le jeton associé à cet appareil côté backend.
#define DEVICE_TOKEN   "REMPLIR_LE_JETON_DE_L_APPAREIL"

// --- Backend HTTP -----------------------------------------------------------
#define BACKEND_HOST   "192.168.1.50"   // IP ou nom d'hôte du serveur Django
#define BACKEND_PORT   8000

// --- Broker MQTT ------------------------------------------------------------
#define MQTT_HOST      "192.168.1.50"   // souvent la même machine que le backend
#define MQTT_PORT      1883
#define MQTT_USER      ""               // laisser vide si le broker est anonyme
#define MQTT_PASSWORD  ""

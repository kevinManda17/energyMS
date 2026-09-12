#pragma once
// Copier ce fichier en "secrets.h" (NON versionné) et remplir les valeurs.

#define WIFI_SSID      "TON_WIFI"
#define WIFI_PASSWORD  "TON_MOT_DE_PASSE"

// Jeton de l'appareil, à lire dans l'admin Django (RelayState.device_token).
#define DEVICE_TOKEN   "COLLER_LE_JETON_ICI"

// Serveur : IP RÉELLE de la machine sur le WiFi (pas la VM ni Docker).
#define BACKEND_HOST   "192.168.1.50"
#define BACKEND_PORT   8000

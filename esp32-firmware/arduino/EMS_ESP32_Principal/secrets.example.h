#pragma once
// Copier ce fichier en "secrets.h" (NON versionné) et remplir les valeurs.

#define WIFI_SSID      "itel A50C"
#define WIFI_PASSWORD  ""

// Jeton de l'appareil, à lire dans l'admin Django (RelayState.device_token).
#define DEVICE_TOKEN   "_B9RU0WP-hSr_x4OlccnIml50ehpxjzS"

// Serveur : IP RÉELLE de la machine sur le WiFi (pas la VM ni Docker).
#define BACKEND_HOST   "192.168.159.117"
#define BACKEND_PORT   8000

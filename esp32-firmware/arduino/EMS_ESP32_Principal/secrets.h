#pragma once
// ============================================================================
//  EMS IoT — Nœud PRINCIPAL — IDENTIFIANTS.
//
//  CE FICHIER NE DOIT JAMAIS PARTIR SUR GITHUB. Le .gitignore du dossier l'en
//  empêche désormais. Un identifiant poussé une fois reste dans l'historique :
//  le retirer ensuite ne l'efface pas, il faut le changer à la source.
// ============================================================================

// --- WiFi -------------------------------------------------------------------
//  Partage de connexion du téléphone. Réseau OUVERT : mot de passe vide, ce que
//  le pilote interprète comme « pas d'authentification ». Le nom contient une
//  espace, c'est normal et sans effet.
#define WIFI_SSID      "itel A50C"
#define WIFI_PASSWORD  ""

// --- Authentification du nœud auprès du backend -----------------------------
//  À LIRE DANS /admin/ : modèle RelayState, champ device_token, de TA maison.
//
//  L'ancien jeton a été publié sur GitHub le 12/09 : régénère-le avant de
//  t'en servir (Django admin > Relay states > ton micro-réseau > device token).
//  Sans le bon jeton, le backend répond 403 et les lampes ne suivent pas l'app.
#define DEVICE_TOKEN   "_B9RU0WP-hSr_x4OlccnIml50ehpxjzS"

// --- Backend HTTP -----------------------------------------------------------
//  ADRESSE DE LA MACHINE QUI FAIT TOURNER DJANGO, VUE DEPUIS LE PARTAGE DE
//  CONNEXION. Ni « localhost » (qui désignerait l'ESP32 lui-même), ni l'adresse
//  d'une VM ou d'un conteneur Docker.
//
//  Le PC et l'ESP32 doivent être connectés au MÊME réseau — ici le partage de
//  connexion « itel A50C ». Vérifier l'adresse avant de téléverser :
//      Windows : ipconfig        -> « Carte réseau sans fil Wi-Fi », IPv4
//      Linux   : ip addr show    -> l'interface wlan
#define BACKEND_HOST   "192.168.159.117"
#define BACKEND_PORT   8000

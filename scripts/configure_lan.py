#!/usr/bin/env python3
"""
Détecte l'adresse IPv4 LAN du PC et affiche (ou met à jour) les URLs du projet.

    python scripts/configure_lan.py            # affiche seulement
    python scripts/configure_lan.py --write     # met à jour les .env de dev

L'adresse LAN change à chaque réseau (partage de connexion, box, campus…).
Plutôt que de chercher à la main dans `ipconfig`, ce script la détecte et
propose de propager la valeur dans les fichiers .env de développement.

Ce qu'il NE fait pas, volontairement :
  - il ne touche jamais aux fichiers .env.production ni au firmware ESP32
    (l'ESP32 doit être reflashé, on ne peut pas le faire depuis un script) ;
  - il ne modifie rien sans --write.

Limites de la détection automatique, par plateforme :
  - Backend  : fiable (on lit l'interface réellement utilisée pour sortir).
  - Frontend : pas besoin, il déduit l'hôte de la page (voir src/api/baseUrl.js).
  - Mobile   : impossible à deviner depuis le téléphone -> EXPO_PUBLIC_API_BASE_URL.
  - ESP32    : impossible sans mDNS -> constante BACKEND_HOST_STR dans config.h.
"""
from __future__ import annotations

import argparse
import re
import socket
import sys
from pathlib import Path

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

ROOT = Path(__file__).resolve().parent.parent

# Fichier .env de développement -> variables à mettre à jour.
ENV_TARGETS: dict[str, tuple[str, ...]] = {
    "ems-frontend/.env": ("VITE_API_BASE_URL", "VITE_WS_URL"),
    "ems-frontend/.env.example": ("VITE_API_BASE_URL", "VITE_WS_URL"),
    "ems-mobile/.env": ("EXPO_PUBLIC_API_BASE_URL", "EXPO_PUBLIC_EDGE_API_URL"),
    "ems-mobile/.env.example": ("EXPO_PUBLIC_API_BASE_URL", "EXPO_PUBLIC_EDGE_API_URL"),
    "ems-backend/.env": ("LAN_HOST", "DJANGO_ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS",
                         "FRONTEND_URL", "API_BASE_URL", "FRONTEND_BASE_URL",
                         "PUBLIC_APP_BASE_URL"),
    "ems-backend/.env.example": ("LAN_HOST", "DJANGO_ALLOWED_HOSTS",
                                 "CORS_ALLOWED_ORIGINS", "FRONTEND_URL",
                                 "API_BASE_URL", "FRONTEND_BASE_URL",
                                 "PUBLIC_APP_BASE_URL"),
}


def _route_ipv4() -> str | None:
    """IPv4 de l'interface de sortie (socket UDP, aucun paquet émis).

    ⚠ Quand un VPN est actif, c'est le tunnel qui gagne (ex. 10.2.0.2) — or un
    téléphone du LAN ne peut PAS joindre cette adresse. On ne s'en sert donc que
    comme candidat parmi d'autres, jamais comme réponse automatique.
    """
    for probe in ("8.8.8.8", "1.1.1.1"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.5)
            sock.connect((probe, 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            continue
        finally:
            sock.close()
    return None


def candidate_addresses() -> list[str]:
    """Toutes les IPv4 non-loopback vues par la machine."""
    found: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except socket.gaierror:
        pass
    route = _route_ipv4()
    if route and route not in found:
        found.append(route)
    return found


def _rank(ip: str) -> int:
    """Plus le rang est bas, plus l'adresse est plausible comme LAN.

    Les réseaux domestiques et les partages de connexion sont massivement en
    192.168.x et 172.20.x. Le 10.x est fréquemment un tunnel VPN : on le garde
    en dernier recours. 169.254.x (APIPA) signale une interface sans DHCP.
    """
    if ip.startswith("192.168."):
        return 0
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
        except (IndexError, ValueError):
            second = 0
        if 16 <= second <= 31:
            return 1
    if ip.startswith("169.254."):
        return 4          # auto-configuration : interface non fonctionnelle
    if ip.startswith("10."):
        return 3          # souvent un VPN
    return 2


def detect_lan_ipv4() -> str | None:
    """Meilleure adresse LAN plausible, VPN dépriorisé."""
    candidates = candidate_addresses()
    if not candidates:
        return None
    return sorted(candidates, key=_rank)[0]


def values_for(ip: str) -> dict[str, str]:
    api = f"http://{ip}:{BACKEND_PORT}/api"
    front = f"http://{ip}:{FRONTEND_PORT}"
    return {
        "LAN_HOST": ip,
        "API_BASE_URL": api,
        "FRONTEND_BASE_URL": front,
        "PUBLIC_APP_BASE_URL": front,
        "FRONTEND_URL": front,
        "VITE_API_BASE_URL": api,
        "VITE_WS_URL": f"ws://{ip}:{BACKEND_PORT}/ws",
        "EXPO_PUBLIC_API_BASE_URL": api,
        "EXPO_PUBLIC_EDGE_API_URL": api,
        "DJANGO_ALLOWED_HOSTS": f"{ip},localhost,127.0.0.1",
        "CORS_ALLOWED_ORIGINS": f"{front},http://localhost:{FRONTEND_PORT}",
    }


def update_env_file(path: Path, keys: tuple[str, ...], values: dict[str, str]) -> int:
    """Réécrit les clés demandées si elles existent déjà. Retourne le nb de lignes changées.

    On ne réécrit que des lignes `CLE=...` existantes et non commentées : on
    n'ajoute pas de clé, et on ne touche jamais aux commentaires (qui gardent
    l'historique des anciennes adresses).
    """
    if not path.exists():
        return 0
    original = path.read_text(encoding="utf-8")
    updated = original
    changed = 0
    for key in keys:
        if key not in values:
            continue
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        new_line = f"{key}={values[key]}"
        new_text, n = pattern.subn(new_line, updated)
        if n and new_text != updated:
            changed += n
            updated = new_text
    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true",
                        help="met à jour les fichiers .env de développement")
    parser.add_argument("--ip", help="forcer une adresse au lieu de la détecter")
    args = parser.parse_args()

    ip = args.ip or detect_lan_ipv4()
    if not ip:
        print("Impossible de détecter une adresse LAN. Utilisez --ip <adresse>.")
        others = candidate_addresses()
        if others:
            print("Adresses vues sur la machine :", ", ".join(others))
        return 1

    print(f"Adresse LAN détectée : {ip}\n")
    print(f"  Backend  : http://{ip}:{BACKEND_PORT}")
    print(f"  Frontend : http://{ip}:{FRONTEND_PORT}")
    print(f"  API      : http://{ip}:{BACKEND_PORT}/api")
    print(f"  ESP32    : http://{ip}:{BACKEND_PORT}/api/ems/decision/")

    others = [a for a in candidate_addresses() if a != ip]
    if others:
        print(f"\n  (autres interfaces détectées : {', '.join(others)} — "
              f"si le téléphone ne joint pas le PC, essayer celles-ci)")

    if not args.write:
        print("\nAucun fichier modifié. Relancer avec --write pour appliquer.")
        return 0

    values = values_for(ip)
    print("\nMise à jour des fichiers .env de développement :")
    total = 0
    for rel, keys in ENV_TARGETS.items():
        path = ROOT / rel
        n = update_env_file(path, keys, values)
        total += n
        state = f"{n} ligne(s)" if n else ("absent" if not path.exists() else "rien à changer")
        print(f"  {rel:35} {state}")

    print(f"\n{total} ligne(s) mise(s) à jour.")
    print("\nÀ FAIRE MANUELLEMENT (non automatisable) :")
    print(f"  1. ESP32 : mettre BACKEND_HOST_STR = \"{ip}\" dans")
    print("     esp32-firmware/arduino/EMS_ESP32/config.h, puis téléverser.")
    print("  2. Redémarrer le frontend (Vite relit .env au démarrage).")
    print("  3. Mobile : npx expo start --clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())

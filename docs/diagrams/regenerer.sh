#!/usr/bin/env bash
#
# Régénère tous les diagrammes depuis leurs sources.
#
#     cd docs/diagrams && ./regenerer.sh
#
# À lancer après toute modification du modèle de données ou du noyau expert.
# L'ERD, lui, n'a même pas besoin d'être relu : il s'extrait du registre Django
# et décrit donc toujours le schéma du moment. Les diagrammes UML, eux, sont
# écrits à la main — c'est ce script qui les recompile, pas qui les met à jour.
#
set -euo pipefail

ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
SOURCES="$ICI/sources"
SORTIE="$ICI/output"

mkdir -p "$SOURCES" "$SORTIE"

echo "== ERD — extrait du registre Django =="
(cd "$RACINE/ems-backend" && python -m tools.generer_erd) > "$SOURCES/erd_complet.dot"
# Le nombre de tables est affiché sur la sortie d'erreur par le générateur, qui
# échoue bruyamment si le registre est vide : un ERD sans table se dessine très
# bien et ne ressemble pas à une erreur.

for format in svg png pdf; do
  case $format in
    png) dot -Tpng -Gdpi=140 "$SOURCES/erd_complet.dot" -o "$SORTIE/erd_complet.png" ;;
    *)   dot -T$format "$SOURCES/erd_complet.dot" -o "$SORTIE/erd_complet.$format" ;;
  esac
done

echo "== Diagrammes UML =="
plantuml -tsvg -o "$SORTIE" "$SOURCES"/*.puml
plantuml -tpng -o "$SORTIE" "$SOURCES"/*.puml

echo
echo "== Résultat =="
ls -1 "$SORTIE"/*.svg | wc -l | xargs printf "  %s fichiers SVG\n"
ls -1 "$SORTIE"/*.png | wc -l | xargs printf "  %s fichiers PNG\n"

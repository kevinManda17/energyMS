# Diagrammes

Les fichiers `.mmd` sont les **sources** ; les `.svg` en sont la sortie
compilée. La source fait foi.

## Régénérer

```bash
cd docs/diagrams
npx -y @mermaid-js/mermaid-cli@11 -i <fichier>.mmd -o <fichier>.svg
```

## ⚠ SVG en retard sur leurs sources (28/07/2026)

Quatre sources ont été corrigées — elles annonçaient **24 règles** et
`core/defuzzification.py`, alors que le moteur en compte **38 (+ 6 par ligne)**
et que le module s'appelle `core/aggregation.py` depuis la refonte :

| Source corrigée | SVG à régénérer |
|---|---|
| `01-vue-ensemble.mmd` | `01-vue-ensemble.svg` |
| `02-organisation-code-flou.mmd` | `02-organisation-code-flou.svg` |
| `03-pipeline-4-etapes.mmd` | `03-pipeline-4-etapes.svg` |
| `07-boucle-fermee.mmd` | `07-boucle-fermee.svg` |

Les SVG portent encore l'ancien texte. Ils doivent être régénérés avant toute
réutilisation dans le mémoire — la commande ci-dessus suffit, mais elle
télécharge le paquet Mermaid, ce qui n'a pas été fait ici.

Référence à jour du moteur : **[../SYSTEME_EXPERT.md](../SYSTEME_EXPERT.md)**.

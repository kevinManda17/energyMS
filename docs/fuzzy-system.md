# Système expert flou — voir SYSTEME_EXPERT.md

> **Ce document ne décrit plus le moteur.** Source unique :
> **[SYSTEME_EXPERT.md](SYSTEME_EXPERT.md)**.

---

## Pourquoi ce renvoi

Trois documents décrivaient le système expert. Deux le décrivaient **faux** :

| Affirmation périmée | Réalité |
|---|---|
| « 24 règles » | **38 règles maison + 6 règles de ligne** |
| `defuzzification.py` comme module d'agrégation | `aggregation.py` — l'étape n'a jamais été une défuzzification |
| Température batterie « sinon 25 °C » | Le défaut silencieux a été **supprimé** : l'absence vaut `None` et bloque la décision |
| Faits par ligne en « Lot 2 (perspective) » | **Implémentés** : `LineFacts`, `BatteryFacts`, 6 règles de ligne, optimiseur |
| `operating_mode` valant `AUTO` | Vocabulaire unifié sur `AUTOMATIC` |

Le problème n'était pas que ces pages soient en retard, c'est qu'elles
**divergeaient**. Trois descriptions d'un même moteur se contredisent dès la
modification suivante, et le lecteur n'a alors aucun moyen de savoir laquelle
fait foi. Les mettre à jour toutes les trois aurait seulement reporté le
problème d'un cran.

Le fichier est conservé sous son nom pour que les liens existants continuent de
fonctionner.

---

## Où trouver quoi

| Sujet | Document |
|---|---|
| Architecture du moteur : faits, variables linguistiques, règles, agrégation, planchers, cascade, optimiseur | [SYSTEME_EXPERT.md](SYSTEME_EXPERT.md) |
| Protocole des nœuds ESP32, authentification du sondage | [PROTOCOLE_ESP32.md](PROTOCOLE_ESP32.md) |
| Câblage, charges par ligne, réseau, état réel du prototype | [CURRENT_SYSTEM_STATE.md](CURRENT_SYSTEM_STATE.md) |
| Unités, structure d'une mesure, mesure *vs* estimation | [MEASUREMENTS_UNITS.md](MEASUREMENTS_UNITS.md) |

Mesurer le moteur : `cd ems-backend && python -m tools.fuzzy_bench`

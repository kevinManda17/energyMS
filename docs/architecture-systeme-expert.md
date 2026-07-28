# Architecture du système expert flou — voir SYSTEME_EXPERT.md

> **Ce document ne décrit plus le moteur.** Source unique :
> **[SYSTEME_EXPERT.md](SYSTEME_EXPERT.md)**.

---

## Pourquoi ce renvoi

Cette page annonçait décrire « l'implémentation réelle », avec des valeurs
« extraites du code ». Elles ne l'étaient plus :

| Affirmation périmée | Réalité |
|---|---|
| « Inférence (24 règles) » | **38 règles maison + 6 règles de ligne** |
| `defuzzification.py` → « Agrégation (8 scores) » | `aggregation.py` — l'étape n'a jamais été une défuzzification, et l'appeler ainsi égarait quiconque cherchait la méthode employée |
| « sans modifier les 24 règles actuelles » | Les faits contextuels sont désormais **lus par des règles** (R031–R038) |
| Température batterie par défaut à 25 °C | Défaut silencieux **supprimé** : l'absence vaut `None` |
| Faits par ligne annoncés en perspective | **Implémentés**, avec une base de règles dédiée et un optimiseur |

Une page qui affirme décrire le code et ne le décrit plus est **pire qu'une page
absente** : elle inspire confiance à tort. Et trois descriptions d'un même
moteur divergeront de nouveau à la modification suivante — c'est ce qui vient
de se produire.

Le fichier est conservé sous son nom pour que les liens existants continuent de
fonctionner.

---

## Ce que contient SYSTEME_EXPERT.md

1. Le principe d'ensemble et la séparation des couches (diagramme Mermaid)
2. Les faits — maison, par ligne, par batterie — et le traitement de l'absence
3. Les variables linguistiques, leurs univers et leurs termes
4. La base de règles maison, et pourquoi un conséquent rassurant est mort
5. L'agrégation par maximum pondéré, et les planchers de sûreté
6. La cascade de décision (diagramme Mermaid)
7. Les règles par ligne et les vétos
8. L'optimiseur de délestage : formulation, poids, résolution
9. Les mesures avant / après, avec les écarts assumés
10. Les propriétés vérifiées par les tests
11. Ce qui reste ouvert

Mesurer le moteur : `cd ems-backend && python -m tools.fuzzy_bench`

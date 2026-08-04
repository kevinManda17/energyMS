# Refonte du délestage et retrait de l'autonomie

Branche `refonte-delestage`, non fusionnée. Trois commits, un par tâche.

> **Le système expert décide** s'il faut délester, quelles lignes sont
> autorisées, lesquelles sont interdites et dans quel ordre les traiter.
> **Le back-end exécute.** Il ne recalcule pas, ne complète pas, et ne peut pas
> contredire.

---

## 1. Fichiers

### Créés

| Fichier | Lignes | Objet |
|---|---:|---|
| `apps/fuzzy_engine/core/shedding.py` | 468 | Le plan de délestage, produit par le moteur |
| `tests/test_shedding.py` | 387 | 31 tests, groupés par garantie, sans Django |
| `tools/scenarios_delestage.py` | 287 | Six situations jouées contre le moteur réel |

### Supprimés

| Fichier | Lignes | Pourquoi |
|---|---:|---|
| `apps/fuzzy_engine/core/optimizer.py` | 478 | Pouvait annuler la décision du moteur |
| `apps/fuzzy_engine/core/autonomy.py` | 87 | Grandeur dérivée, pas un fait |
| `tests/test_optimizer.py` | 246 | Testait l'optimalité d'une combinaison — objet disparu |

### Modifiés

| Fichier | Δ lignes | Ce qui change |
|---|---:|---|
| `core/rules.py` | 93 | R026/R027/R036 retirées ; prémisse de relâchement ; R006/R021/R022 |
| `core/membership.py` | −72 | `soc_at_least_medium` ajoutée, quatre fonctions d'autonomie retirées |
| `core/facts.py` | 34 | Clés d'autonomie retirées, `soc_at_least_medium` exposée |
| `core/models.py` | 29 | `LineFacts.priority_source`, propriété `shed_plan` |
| `core/decision_mapper.py` | 26 | Produit le plan, uniquement en mode automatique |
| `core/engine.py` | −16 | Dérivation de l'autonomie retirée |
| `actuator.py` | — | `_optimized_plan` et `_BatteryView` retirés ; lit le plan |
| `apps/fuzzy_engine/engine.py` | — | `priority_source` renseigné, `autonomy_hours` retiré |
| `tools/fuzzy_bench.py` | −85 | `measure_autonomy` et sa grille retirées |

**Bilan : 1 608 lignes ajoutées, 1 245 retirées** sur le périmètre de la refonte.

---

## 2. Mesures — 222 750 situations

| Mesure | Avant | Après | Attendu | |
|---|---:|---:|---|---|
| Inversions **échelle de danger** | 0 | **0** | 0 avant, 0 après | ✅ |
| Inversions barème strict | 19 | **21** | ≈ 21 | ✅ |
| Amplitude max. des creux de risque, axe SOC | — | **0,6875 pt** | < 1 pt / 100 | ✅ |
| Part de `SHED_NON_PRIORITY_LOAD` | 2,78 % | **0,99 %** | ≈ 2,8 → ≈ 1,0 % | ✅ |
| Risque moyen | 87,73 | **84,58** | ≈ 84,6 | ✅ |
| Écart-type du risque | 19,60 | **22,24** | ≈ 22,2 | ✅ |
| Inertie du bilan **hors planchers** | 29,33 % | **0,00 %** | 0,00 % | ✅ |
| Règles | 38 | **35** | 35 | ✅ |
| Conséquents morts / sur indicateur non lu | 0 / 0 | **0 / 0** | 0 / 0 | ✅ |

### Interprétation

**La propriété de sûreté tient.** Zéro inversion sur l'échelle de danger, avant
comme après : la gravité de la décision ne décroît jamais quand le danger croît.
C'est la seule propriété exigible, et elle est intacte.

**Les 21 inversions au barème strict sont toutes des opportunités qui
disparaissent** — vérifié sur les échantillons des trois axes concernés : toutes
aboutissent à `NORMAL_OPERATION` depuis `CHARGE_BATTERY` ou `USE_BATTERY`.
Cesser de charger parce que la production baisse n'est pas un relâchement face
au danger.

**Le moteur déleste presque trois fois moins** (2,78 % → 0,99 %) et devient
**moins alarmiste mais plus discriminant** : le risque moyen baisse de 3,2
points pendant que son écart-type gagne 2,6 points. Il distingue mieux les
situations au lieu de les saturer toutes au même niveau. C'est l'effet conjoint
de la correction de R006 et de la prémisse de relâchement.

**L'inertie du bilan prévisionnel hors planchers tombe à zéro.** Dans la fenêtre
où la batterie est saine, faire varier le bilan sur toute son étendue change
désormais la décision dans **100 %** des groupes. La prévision cesse d'être un
affichage.

### Un écart à signaler

Les **creux du score de risque sur l'axe SOC passent de 99 à 133**. Ce n'est pas
une dégradation : leur amplitude maximale reste à 0,6875 point sur 100, sous
tout seuil de décision, et l'échelle de danger n'en présente aucune. Le nombre
augmente parce que le moteur est **moins souvent saturé** — un score qui varie
davantage présente mécaniquement plus de micro-creux. L'écart-type le confirme.

---

## 3. Les six scénarios

```
SOC critique                            PROTECT_BATTERY          [1, 3]
Temperature batterie dangereuse         PROTECT_BATTERY          [1, 3]
Deficit avec charges non prioritaires   SHED_NON_PRIORITY_LOAD   [1]
Presence d'une charge critique          PROTECT_BATTERY          [1, 3]
Donnees insuffisantes ou incoherentes   BLOCK_AUTOMATIC_ACTION   aucun plan
Absence de deficit                      CHARGE_BATTERY           aucun plan
```

Conforme à la cible attendue, scénario par scénario.

Le **quatrième** mérite lecture : la ligne 2 porte un respirateur. Le moteur
protège la batterie en coupant 1 et 3, et la trace montre le veto `L003` qui
épargne la 2. La protection batterie ne l'emporte pas sur une charge vitale.

Le **cinquième** montre la différence entre « rien à couper » et « la question
ne se pose pas » : la décision étant bloquée, aucun plan n'est produit — pas
même un plan vide.

`python -m tools.scenarios_delestage` affiche pour chacun les faits en entrée,
les règles maison avec leur activation, les règles de ligne avec leurs scores et
leurs vetos, l'ordre imposé, les coupures, les interdictions, le motif d'arrêt,
l'état commandé et l'explication en français.

---

## 4. Tests

**220 tests passent** (189 avant la tâche 4, 148 au départ de la branche).

`tests/test_shedding.py` en apporte 31, groupés par garantie : interdictions
absolues, la décision produit l'action qu'elle annonce, ordre, absence de plan,
disparition de l'autonomie, origine de la priorité.

---

## 5. Limites restantes

**Aucun rétablissement pendant les modes de recommandation.** Une ligne coupée
le reste tant que la décision n'est pas redevenue automatique. En `ECO_MODE` ou
`DATA_QUALITY_ALERT`, le moteur ne commande rien — c'est voulu, l'humain garde
la main — mais la conséquence est qu'une ligne délestée pendant un épisode
attend un retour en mode automatique pour être rallumée. Sur un micro-réseau
dont la qualité des données se dégrade durablement, elle peut le rester
longtemps.

**Le relâchement est plus grossier depuis le retrait de l'autonomie.**
L'autonomie *rapportait la réserve à la consommation* ; `soc_at_least_medium` ne
le fait pas. Une batterie à 50 % est ample pour 24 W et dérisoire pour 2 kW, et
le SOC seul ne distingue plus ces deux situations. C'est le prix assumé de la
simplification, et il faut le savoir en lisant les décisions nocturnes.

**`batteries` est devenu un fait sans influence dans le noyau.** L'autonomie en
était l'unique lectrice. Le parc reste utile côté assembleur Django — qui en
dérive le SOC agrégé et la température retenue — mais aucune règle ne le lit
plus. Le test d'influence porte l'exception **par écrit** plutôt que de la
tolérer en silence : le jour où une règle lira de nouveau le parc, il faudra
l'en retirer sciemment.

**Le repli de rang subsiste** pour les micro-réseaux sans faits de ligne. Sa
présence est marquée `fallback_rank_used` dans la trace : elle signale une
télémétrie absente, pas un mode de fonctionnement normal.

**La garantie « une seule coupure » porte sur l'épisode, pas sur le cycle.**
Elle repose sur `already_shed`, qui constate qu'une ligne délestable est déjà
ouverte. Si une ligne est ouverte pour une autre raison — intervention manuelle,
défaut matériel — le moteur la lira comme un délestage déjà en place et
s'abstiendra de couper. Prudent, mais pas toujours ce qu'on veut.

---

## 6. Vérifier soi-même

```bash
cd ems-backend
python -m tools.fuzzy_bench --compare /tmp/avant.json
python -m tools.scenarios_delestage
pytest tests/
```

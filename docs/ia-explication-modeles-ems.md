# Explication — modèles d'IA et intelligence du système EMS

Ce document **explique**, de manière pédagogique, la discussion sur les modèles
d'intelligence artificielle applicables à l'EMS (contenu du PDF partagé). Il
sert de référence pour comprendre le rôle de chaque brique. Il ne décrit pas
seulement ce qui est codé aujourd'hui : voir `docs/ia-architecture-et-roadmap.md`
pour la distinction **réalisé / perspective**.

---

## 0. Idée directrice

Un EMS moderne ne cherche pas à tout résoudre avec **un seul modèle**. Il
combine plusieurs formes d'IA, chacune répondant à une question différente :

| Brique | Question à laquelle elle répond |
| --- | --- |
| Prévision supervisée | « Que va-t-il probablement se passer ? » |
| Détection non supervisée | « Y a-t-il quelque chose d'anormal ? » |
| Optimisation mathématique | « Quelle est la meilleure décision sous contraintes ? » |
| Système expert flou | « Cette décision est-elle sûre et conforme aux règles ? » |
| Apprentissage par renforcement | « Puis-je apprendre une meilleure stratégie par essai/erreur ? » |

L'enchaînement logique : **capteurs → prétraitement → prévision → (anomalies) →
optimisation → validation floue → commande des relais**.

---

## 1. Apprentissage supervisé — la prévision (la base)

**Principe.** « Supervisé » signifie que l'on apprend à partir de données dont on
connaît déjà la **valeur cible** (l'étiquette). Ici la cible est une valeur
future connue dans l'historique : la consommation ou la production dans 10 min.

**Deux modèles séparés** (car les phénomènes diffèrent) :

```
P̂_load(t+10) = f_load( P_load(t), P_load(t-1), heure, jour, … )
P̂_PV(t+10)   = f_PV( irradiance, température, heure, production passée, … )
```

- Consommation : dépend des **usages** et du **temps** (heure, jour, week-end).
- Production PV : dépend de l'**environnement** (irradiance, température, heure).

**Modèles candidats** : régression linéaire (référence), Random Forest,
Gradient Boosting / XGBoost, SVR, et LSTM/GRU quand les séquences temporelles
sont assez nombreuses.

**Règle d'or.** Le modèle de prévision **ne commande jamais** les relais : il
fournit seulement une prévision au module de décision.

---

## 2. Apprentissage non supervisé — anomalies et profils

**Principe.** « Non supervisé » = pas d'étiquette « normal / panne / surcharge ».
On laisse l'algorithme trouver lui-même la structure des données.

### A. Détection d'anomalies
Repérer un comportement inhabituel, par exemple :
- consommation anormalement élevée ;
- capteur bloqué sur une valeur constante ;
- brusque variation de courant ;
- consommation alors qu'une charge est censée être éteinte ;
- écart anormal entre la puissance globale et les sous-compteurs ;
- production solaire incohérente avec l'irradiance.

Algorithmes : **Isolation Forest**, **DBSCAN**, Local Outlier Factor,
autoencodeur (version avancée).

### B. Regroupement de profils (clustering)
**K-means** peut classer des journées : faible consommation, normale, forte,
pointe matinale, pointe nocturne. Le numéro de cluster devient ensuite une
**variable d'entrée supplémentaire** pour l'optimiseur ou le système expert.

**Règle de sécurité.** Le non-supervisé **ne coupe jamais** une charge tout seul :
il produit une **alerte / un indice d'anomalie**, vérifié ensuite par les autres
modules.

---

## 3. Optimisation mathématique — transformer la prévision en décision

**Principe.** La prévision dit ce qui va se passer ; l'optimisation calcule la
**meilleure décision** compte tenu des prévisions **et des contraintes physiques**.

**Variables de décision** (à chaque pas `t`) : puissance de charge `P_ch(t)` et
de décharge `P_dis(t)` de la batterie, état marche/arrêt `x_i(t)` de chaque
charge, puissance réseau `P_grid(t)`, énergie solaire utilisée directement.

**Équilibre énergétique** (ce qui entre = ce qui sort) :
```
P_PV(t) + P_grid(t) + P_dis(t) = P_load(t) + P_ch(t) + P_loss(t)
```

**Évolution de l'état de charge de la batterie** :
```
SOC(t+1) = SOC(t) + (η_ch · P_ch(t) · Δt) / E_bat
                  − (P_dis(t) · Δt) / (η_dis · E_bat)

avec :  SOC_min ≤ SOC(t) ≤ SOC_max
        0 ≤ P_ch(t) ≤ P_ch_max ,  0 ≤ P_dis(t) ≤ P_dis_max
        (charge et décharge jamais simultanées)
```

**Fonction objectif** (ce que l'on cherche à minimiser) :
```
min J = Σ_t [ α·C_énergie(t)      ← coût de l'énergie
            + β·P_non_servie(t)    ← pénalité si une charge n'est pas alimentée
            + γ·C_dégradation(t)   ← usure de la batterie
            + δ·P_pointe(t)        ← pointes de consommation
            + μ·N_commutations(t)  ← trop d'ouvertures/fermetures de relais
            − λ·P_PV_utilisée(t) ] ← bonus d'autoconsommation solaire
```
Usure batterie approximée : `C_dégradation = c_deg · (P_ch + P_dis) · Δt`
(pénaliser l'énergie qui transite par la batterie évite de l'user pour un petit
gain immédiat).

**Méthode recommandée : MPC basé sur un MILP.**
- **MILP** (programmation linéaire en nombres entiers) car les relais sont des
  variables **binaires** (0/1).
- **MPC** (contrôle prédictif) = on résout le problème toutes les 10 min, on
  applique **seulement la première décision**, puis on recommence avec les
  nouvelles mesures.

---

## 4. Apprentissage par renforcement (RL) — apprendre par essai/erreur

**Principe.** Un **agent** apprend une stratégie en interagissant avec le
système et en recevant une **récompense**. Il découvre quelles actions
maximisent la récompense sur le long terme.

**Sécurité d'abord.** On ne branche **jamais** l'agent directement sur les relais
physiques : il apprend d'abord dans une **simulation** du micro-réseau
(environnement type Gymnasium).

**État** de l'agent :
```
s_t = [ SOC, P_PV, P̂_PV(t+10), P_load, P̂_load(t+10), état des charges, heure, … ]
```
(on peut ajouter température, irradiance, priorités, disponibilité réseau,
anomalie détectée, tarif).

**Actions** (version discrète) : maintenir les charges / couper la charge non
prioritaire / la réactiver / charger la batterie / décharger / ne rien changer.

**Récompense** :
```
r_t = − ( α·C + β·E_non_servie + γ·D_batterie + δ·P_pointe + μ·N_commutations )
      + λ·E_solaire_utilisée
```
La pénalité pour une charge **prioritaire** non servie doit être **très
supérieure** à celle d'une charge non prioritaire (`β_prioritaire ≫ β_non_prio`) :
l'agent apprend ainsi que couper une charge prioritaire est bien plus grave.

**Algorithmes** : Q-learning (états très limités) → **DQN** (états continus,
actions discrètes) → **PPO** (plus stable) → SAC/DDPG (puissance continue).
Pour un mémoire, DQN ou PPO est défendable, **à condition de comparer** l'agent à
une stratégie classique.

---

## 5. Optimisation vs renforcement — pas des concurrents

- **Option 1 — Optimisation seule** : `prévisions → MILP/MPC → décision`.
  La plus sûre, la plus facile à justifier mathématiquement.
- **Option 2 — RL seul** : `état → agent → action`. Plus adaptatif, plus
  difficile à garantir/valider.
- **Option 3 — Hybride (recommandée)** :
  ```
  prévisions supervisées → optimisation → décision proposée
                         → système expert flou + sécurité → action
  ```
  Puis, en **expérimentation**, comparer « optimiseur classique » vs « agent RL »
  sur : coût total, autoconsommation, énergie non servie, nombre de coupures,
  état/cycles batterie, temps de calcul, respect des contraintes.

---

## 6. Ordre d'implémentation conseillé

1. Finaliser la prévision supervisée (consommation + PV).
2. Ajouter la détection d'anomalies (Isolation Forest / DBSCAN).
3. Écrire le modèle mathématique (objectif, variables, contraintes).
4. Implémenter un optimiseur MILP/MPC (toutes les 10 min).
5. Utiliser le système expert flou comme couche de validation/sécurité.
6. Créer un environnement simulé (Gymnasium).
7. Entraîner un agent DQN/PPO **en simulation seulement**.
8. Comparer l'agent au MILP/MPC.
9. Éventuellement, laisser l'agent **recommander** sans lui donner le contrôle
   physique direct.

**Contribution scientifique visée** : un système hybride associant prévision
supervisée, détection non supervisée d'anomalies, optimisation prédictive sous
contraintes et système expert flou, avec évaluation expérimentale d'une
stratégie d'apprentissage par renforcement — chaque module ayant un rôle précis.

---

## 7. « IA générale » ? Agent conversationnel vs superviseur intelligent

Deux notions à ne pas confondre :

- **Agent conversationnel** = l'**interface** en langage naturel (« la bouche »).
  Il répond : « Combien ai-je consommé ? », « Pourquoi la prise non prioritaire
  a-t-elle été coupée ? », « État de la batterie ? ». Seul, il ne « comprend »
  rien : il doit être **connecté** aux données et modules de l'EMS.
- **Superviseur intelligent** = le **cerveau de coordination**. Il agrège l'état
  global (mesures, prévisions, anomalies, décisions, alertes) et produit
  explications et recommandations.

**Comment lui faire « comprendre » le système ?** En construisant un **état
global** `X_t` à chaque instant, par exemple :
```json
{
  "production_pv_w": 180,
  "consommation_totale_w": 320,
  "batterie_soc": 42,
  "charge_prioritaire_w": 35,
  "charge_non_prioritaire_w": 250,
  "prediction_consommation_10min_w": 390,
  "prediction_pv_10min_w": 130,
  "anomalie_detectee": false,
  "decision_optimiseur": "couper_charge_non_prioritaire",
  "raison": "production insuffisante et batterie faible"
}
```
Le superviseur combine ces éléments pour expliquer : « La charge non prioritaire
a été coupée car la consommation prévue dépasse la production solaire et la
batterie est descendue à 42 %. La charge prioritaire reste alimentée. »

**Trois niveaux d'intégration** :
1. **Consultation** : lecture seule (affiche, explique, résume). Ne commande rien.
2. **Recommandation** : propose une action, l'utilisateur **confirme**.
3. **Supervision** : exécute une action **uniquement** via la chaîne de sécurité
   `permissions → règles électriques → système expert → commande → relais`.

**Interdits absolus** : couper une charge prioritaire sans validation, décharger
la batterie sous son seuil, dépasser la puissance de l'onduleur, réactiver une
charge pendant une surcharge, ignorer une alerte, modifier seul les règles de
sécurité.

**Ce n'est pas une IA générale.** Le système reste **spécialisé** (surveillance,
prévision, optimisation, gestion des charges, explication). C'est donc une
**IA spécialisée multi-modules**, dotée d'un agent conversationnel comme
interface — pas une intelligence artificielle générale.

**Position pour le mémoire** :
- *Système actuel* : l'agent conversationnel = interface intelligente pour
  interroger l'EMS et recevoir des explications.
- *Perspectives* : évolution vers un superviseur intelligent capable de
  coordonner les modules et de proposer/exécuter des actions sous contraintes.
- Formule : « L'agent conversationnel est la bouche et l'interface du système ;
  le superviseur intelligent est son cerveau de coordination ; les modèles,
  l'optimiseur et le système expert sont ses modules de décision spécialisés. »

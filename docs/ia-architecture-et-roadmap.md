# IA du système EMS — architecture actuelle et feuille de route

Ce document clarifie **ce qui est réellement implémenté** dans l'IA de l'EMS et
**ce qui reste une perspective**, pour éviter toute incohérence entre le mémoire,
le code et les propositions d'architecture hybride discutées.

> Règle de lecture : chaque brique est étiquetée
> **[RÉALISÉ]**, **[PARTIEL]** ou **[PERSPECTIVE]**.

---

## 1. Vue d'ensemble : IA spécialisée multi-modules

Le système EMS n'est **pas** une intelligence artificielle générale. C'est une
**IA spécialisée, composée de plusieurs modules**, dédiée à la surveillance, la
prévision, la décision et l'explication énergétiques. Un éventuel agent
conversationnel n'en serait que l'**interface**, pas le cœur.

```
Capteurs / ESP32
   ↓
Backend + base de données (état global du micro-réseau)
   ↓
Modules intelligents :
   ├── Prévision supervisée            [RÉALISÉ]
   ├── Détection d'anomalies (non sup.) [PERSPECTIVE]
   ├── Optimisation mathématique        [PERSPECTIVE]
   ├── Système expert flou              [RÉALISÉ]
   └── Apprentissage par renforcement   [PERSPECTIVE]
   ↓
Décision → commande des relais (ESP32)
   ↓
(futur) Superviseur intelligent + agent conversationnel  [PERSPECTIVE]
```

---

## 2. Ce qui est réellement implémenté

### 2.1 Prévision supervisée — [RÉALISÉ]

- **Consommation** : modèle **GRU** (Keras), rollout autorégressif, pas de 10 min.
- **Production PV** : **Random Forest** actif (prédiction à plat par horizon à
  partir de la météo Open-Meteo) ; le **LSTM** reste enregistré en référence.
- Modèles entraînés hors-ligne puis enregistrés via `python manage.py register_models`.
- Le modèle **ne commande jamais** les relais : il fournit une prévision au
  module de décision. (Conforme au principe du PDF.)

### 2.2 Système expert flou — [RÉALISÉ]

- 24 règles floues, fonctions d'appartenance triangulaires/trapézoïdales.
- Entrées : production/consommation/SoC/température **réelles** + prévisions +
  priorité des charges + qualité des données.
- Sorties : 1 décision parmi 9, mode d'exécution, niveau d'alerte, règles
  activées (explicabilité). Voir `docs/architecture-systeme-expert.md`.
- **Rôle actuel : décideur principal.** (Différence avec le PDF, cf. §4.)

### 2.3 Chaîne temps réel — [RÉALISÉ]

- Le nœud ESP32 envoie son relevé (`/api/ems/decision/`) → persisté comme
  mesures réelles → le moteur expert décide sur ces mesures → réponse
  `L1=x;L2=x;L3=x` → relais.
- Garde-fou de sécurité local sur l'ESP32 (seuils de puissance).

---

## 3. Extensions proposées (perspectives, non implémentées)

### 3.1 Détection d'anomalies non supervisée — [PERSPECTIVE]

Utile car les données n'ont pas d'étiquettes « normal / panne / surcharge ».
- Exemples : capteur bloqué, sur-consommation, incohérence puissance/sous-compteurs,
  production incohérente avec l'irradiance.
- Algorithmes : **Isolation Forest**, **DBSCAN**, Local Outlier Factor, autoencodeur.
- Regroupement de profils de journées : **K-means**.
- Principe de sécurité : le non-supervisé **ne coupe jamais** une charge ; il
  produit une **alerte / un indice d'anomalie** vérifié par les autres modules.

### 3.2 Optimisation mathématique (MILP / MPC) — [PERSPECTIVE]

Transforme les prévisions en décision optimale sous contraintes.

Variables de décision par intervalle `t` : `P_ch(t)`, `P_dis(t)`, état `x_i(t)`
des charges, `P_grid(t)`, énergie solaire utilisée.

Équilibre énergétique :
```
P_PV(t) + P_grid(t) + P_dis(t) = P_load(t) + P_ch(t) + P_loss(t)
```

Dynamique de l'état de charge :
```
SOC(t+1) = SOC(t) + (η_ch · P_ch(t) · Δt)/E_bat − (P_dis(t) · Δt)/(η_dis · E_bat)
SOC_min ≤ SOC(t) ≤ SOC_max ;  0 ≤ P_ch ≤ P_ch_max ;  0 ≤ P_dis ≤ P_dis_max
(charge et décharge non simultanées)
```

Fonction objectif proposée :
```
min J = Σ_t [ α·C_énergie + β·P_non_servie + γ·C_dégradation
              + δ·P_pointe + μ·N_commutations − λ·P_PV_utilisée ]
```
Dégradation batterie approximée : `C_dégradation = c_deg · (P_ch + P_dis) · Δt`.

Méthode recommandée : **MPC basé sur un MILP** (relais = variables binaires),
ré-exécuté toutes les 10 min ; on applique seulement la première décision.

### 3.3 Apprentissage par renforcement — [PERSPECTIVE]

- **Ne jamais** connecter directement l'agent aux relais physiques : il apprend
  d'abord dans une **simulation** (environnement type Gymnasium).
- État : `[SOC, P_PV, prév_PV, P_load, prév_load, état charges, heure, …]`.
- Actions discrètes : maintenir / couper la charge non prioritaire / recharger /
  décharger / ne rien changer.
- Récompense : négatif du coût + pénalités (énergie non servie, dégradation,
  pointe, commutations) + bonus autoconsommation. Pénalité charge **prioritaire**
  non servie ≫ non prioritaire.
- Algorithmes : Q-learning (états limités) → **DQN** (actions discrètes) → PPO
  (plus stable) → SAC/DDPG (puissance continue).
- **Toujours comparer** l'agent RL à une stratégie classique (l'optimiseur).

### 3.4 Superviseur intelligent + agent conversationnel — [PERSPECTIVE]

- **Superviseur intelligent** = cerveau de coordination : agrège l'état global
  (mesures, prévisions, anomalies, décisions, alertes) et produit explications /
  recommandations.
- **Agent conversationnel** = interface en langage naturel (la « bouche »), pas
  le cœur. Il répond « pourquoi la charge a été coupée », « état batterie », etc.
- Niveaux d'intégration : (1) consultation seule, (2) recommandation avec
  confirmation utilisateur, (3) exécution **uniquement** via la couche de
  sécurité (permissions → règles électriques → système expert → relais).
- **Interdits** : couper une charge prioritaire sans validation, décharger sous
  le seuil batterie, dépasser la puissance de l'onduleur, ignorer une alerte.

> Cadrage mémoire : l'agent conversationnel / superviseur reste une
> **perspective future**, jamais présenté comme une fonctionnalité centrale.

---

## 4. Point de cohérence à ne pas confondre

Deux architectures coexistent dans les discussions ; elles diffèrent par le
**rôle du système expert flou** :

| | Système **actuel** [RÉALISÉ] | Système **cible hybride** [PERSPECTIVE] |
| --- | --- | --- |
| Décideur | Le **système expert flou** décide | L'**optimiseur (MILP/MPC)** décide |
| Rôle du flou | Décision + sécurité | **Validation** / garde-fou de sécurité |
| Prévision | Alimente le flou | Alimente l'optimiseur |

→ Dans le mémoire, décrire le flou comme **décideur** pour l'existant, et
présenter l'optimiseur comme une **évolution** qui le ferait passer au rôle de
couche de validation.

---

## 5. Ordre d'implémentation conseillé

1. Finaliser la prévision supervisée (conso + PV). **[fait]**
2. Ajouter la détection d'anomalies (Isolation Forest / DBSCAN).
3. Écrire le modèle mathématique (objectif, variables, contraintes).
4. Implémenter un optimiseur MILP/MPC exécuté toutes les 10 min.
5. Utiliser le système expert flou comme couche de validation.
6. Créer un environnement simulé (Gymnasium).
7. Entraîner un agent DQN/PPO **en simulation seulement**.
8. Comparer l'agent au MILP/MPC (coût, autoconsommation, énergie non servie,
   coupures, cycles batterie, temps de calcul, respect des contraintes).
9. Éventuellement autoriser l'agent à **recommander**, sans contrôle physique direct.

**Contribution scientifique visée** : un système hybride associant prévision
supervisée, détection non supervisée d'anomalies, optimisation prédictive sous
contraintes et système expert flou, avec évaluation expérimentale d'une stratégie
d'apprentissage par renforcement — chaque module ayant un rôle précis.

---

## 6. Positionnement pour le mémoire (synthèse)

- **Réalisé** : IoT + prévision supervisée (GRU/RF) + **système expert flou
  décideur** + supervision web/mobile + chaîne temps réel ESP32.
- **Perspectives** : non-supervisé (anomalies), optimisation MILP/MPC,
  apprentissage par renforcement, superviseur intelligent + agent conversationnel.
- **À ne pas affirmer** : que l'optimisation, le RL ou l'agent conversationnel
  sont déjà implémentés ; que le système est une IA générale (il est spécialisé).

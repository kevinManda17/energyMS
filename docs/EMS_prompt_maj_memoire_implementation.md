# PROMPT FINAL — Mise à jour du mémoire EMS (chapitre Implémentation, notes Méthodologie)

> Ce document a été produit après audit direct du code source du projet `energyMS`
> (backend Django, firmware ESP32, application mobile, interface web, edge-gateway).
> Il est destiné à être copié tel quel et donné à un autre assistant pour mettre à jour
> le mémoire *« Conception d'un écosystème IoT pour la gestion intelligente de l'énergie
> et applications multiplateformes dédiées »*, sans déformer le travail réellement effectué.

---

## 0. Instructions générales pour l'assistant qui recevra ce prompt

Tu vas m'aider à corriger le chapitre **4 (Implémentation)** de mon mémoire de licence, et à
signaler (sans les réécrire complètement pour l'instant) quelques points du chapitre **3
(Méthodologie)** qui devront être révisés plus tard.

Règles impératives :
1. **Ne présente jamais un élément non implémenté comme s'il était déjà réalisé.** Distingue
   systématiquement : *réalisé*, *partiel*, *absent*, *phase de test uniquement*, *perspective*.
2. **Ne fabrique aucun résultat expérimental, aucune capture d'écran, aucun chiffre.** Si une
   donnée manque (ex. résultat d'un test physique), écris explicitement qu'elle doit être
   complétée par l'auteur, ne l'invente pas.
3. Le sujet du mémoire n'est **pas** un LLM / une IA générative. S'il faut mentionner un
   assistant de développement ou un LLM utilisé pour produire du code, cela reste au niveau
   des outils de développement (comme on citerait un IDE), jamais comme composant du système
   EMS lui-même, et jamais dans le corps scientifique du mémoire — seulement, si pertinent,
   dans les perspectives ou une note méthodologique très courte.
4. Style académique, français correct, sans emoji, sans ton commercial.
5. Ne fabrique pas de références bibliographiques. Si une section a besoin d'une référence,
   indique `[REF A COMPLETER]` à l'endroit exact et explique brièvement quel type de source
   conviendrait (norme, article, datasheet composant, etc.).
6. Le dossier `edge-gateway/` est conservé dans le dépôt mais n'est **pas intégré à la
   démonstration actuelle** du système (voir section 5 ci-dessous) — ne le présente donc
   jamais comme une brique opérationnelle du prototype démontré, uniquement comme un module
   développé en parallèle / une base pour une architecture Edge-Cloud future.
7. Chaque affirmation technique que tu écris doit pouvoir être rattachée à un fichier réel du
   dépôt (donné en section 8). Si tu n'es pas sûr qu'un détail soit vrai, pose la question à
   l'auteur au lieu de l'écrire.

---

## 1. Synthèse de l'implémentation réelle (état des lieux vérifié par audit de code)

Le projet est structuré en **quatre sous-systèmes logiciels indépendants** plus un
**prototype matériel** :

1. **Backend Django** (`ems-backend/`) : plateforme EMS complète et opérationnelle —
   gestion des maisons/micro-réseaux, capteurs, équipements, mesures, prévisions (ML réel),
   système expert flou, alertes, rapports. Exposée via API REST, consommée par une interface
   web et une application mobile toutes deux fonctionnelles.
2. **Firmware ESP32** (`esp32-firmware/`) : prototype de nœud IoT autonome, aligné sur le
   câblage physique réel à 3 lignes (relais + capteurs de tension/courant). Fonctionne
   actuellement **en local, sans réseau** (voir section 4).
3. **Application mobile** (`ems-mobile/`) et **interface web** (`ems-frontend/`) : deux
   clients complets et fonctionnels du backend, à la granularité *maison / micro-réseau*.
4. **Edge-gateway** (`edge-gateway/`) : module MQTT + cache local + synchronisation, présent
   et fonctionnel en tant que code, mais **non branché** dans la démonstration actuelle.

**Constat transversal le plus important à intégrer au mémoire** : le backend, le moteur
expert, les mesures et les deux interfaces raisonnent tous à l'échelle de **la maison /
micro-réseau entier**. Aucun modèle de données, aucune règle floue, aucun écran ne
représente aujourd'hui une notion de **ligne électrique individuelle (ligne 1/2/3) ou de
canal de relais (IN1/IN3/IN6)**. Le firmware ESP32, lui, raisonne bien à l'échelle des 3
lignes physiques, mais **son lien prévu avec le vrai backend Django est un contrat HTTP
imaginé qui ne correspond à aucune route réellement existante côté serveur** (détails
section 4). La boucle complète décrite dans la méthodologie
(*capteurs → ESP32 → backend → système expert → décision → ESP32 → relais → charges*)
n'est donc **pas encore fermée de bout en bout** ; ce qui existe, ce sont deux moitiés
fonctionnelles séparées :
- la moitié logicielle « maison entière » (mesures génériques → prévision → décision →
  interfaces), pleinement opérationnelle et démontrable ;
- la moitié matérielle « 3 lignes » (mesure RMS + relais + garde-fou de puissance local),
  opérationnelle en mode manuel/local, non encore raccordée au backend.

C'est ce point qui doit être présenté **honnêtement** dans le chapitre Implémentation,
plutôt que comme une intégration déjà bouclée.

---

## 2. Sections du mémoire à mettre à jour, et contenu exact à intégrer

### 2.1 Chapitre 4.2 — Environnement technologique et organisation du projet

Ajouter un paragraphe sur l'environnement de développement du nœud IoT, distinct de la
chaîne Python/Django/React déjà décrite :

> Le nœud IoT du prototype est développé en C++ (framework Arduino) pour une carte
> **ESP32 DevKit**, à l'aide de **PlatformIO** (fichier `platformio.ini`, carte `esp32dev`),
> avec une variante de mise en service testée sous **Arduino IDE 1.8.19** (paquet de cartes
> *esp32 by Espressif Systems*, version 2.0.14). Le code est organisé dans un dossier dédié
> `esp32-firmware/` (`platformio.ini`, `include/config.h` pour la configuration, `src/main.cpp`
> pour la logique).

Préciser aussi, en une phrase, que `edge-gateway/` (Python, FastAPI, paho-mqtt, SQLite) existe
dans l'organisation du dépôt mais correspond à un module distinct décrit à la section
consacrée aux limites (ne pas le développer ici).

### 2.2 Nouvelle sous-section 4.6.7 — Implémentation du nœud IoT ESP32 (prototype 3 lignes)

Insérer cette sous-section **après 4.6.6 (persistance) et avant 4.7 (interface)**, car elle
décrit une brique matérielle du même niveau que le backend, mais physiquement séparée.

Contenu à rédiger (base factuelle vérifiée, à mettre en forme académique) :

- **Objectif du prototype** : démontrer, sur trois lignes électriques indépendantes issues
  d'un onduleur 12V→220V alimenté par panneau solaire + régulateur + batteries, la mesure de
  tension/courant et la commande individuelle de charges par relais.
- **Câblage de puissance** : un conducteur (« fil rouge », considéré comme phase du
  prototype) issu de l'onduleur est divisé en trois arrivées vers un module relais 8 canaux,
  dont 3 canaux sont utilisés (canal 1, 3 et 6) ; le retour commun n'est jamais commuté.
  Chaque ligne alimente une charge (lampe 10 W + prise pour les lignes 1 et 2 ; lampe 20 W
  pour la ligne 3).
- **Instrumentation** : un capteur de courant ZMCT103C et un capteur de tension ZMPT101B par
  ligne, placés après la sortie normalement-ouverte (NO) du relais correspondant, le capteur
  de courant ne mesurant que le conducteur contrôlé de sa ligne.
- **Nœud de commande** : ESP32 DevKit, relais sur GPIO25/26/27 (IN1/IN3/IN6), capteurs sur
  GPIO34/35/32/33 et sur les broches d'entrée seule GPIO36 (SP) / GPIO39 (SN) — toutes sur
  l'ADC1, ce qui reste compatible avec l'usage simultané du Wi-Fi (l'ADC2 ne l'est pas).
- **Acquisition de mesure** : la tension/le courant RMS de chaque ligne sont estimés par
  600 échantillons espacés de 500 µs (≈ 300 ms, soit une quinzaine de périodes à 50 Hz), avec
  retrait de la composante continue par calcul de variance
  (`RMS_AC = sqrt(E[x²] − E[x]²)`), sans synchronisation sur le passage par zéro du secteur.
  **Les coefficients de calibration ne sont pas encore déterminés** (valeur par défaut 1.0) :
  les grandeurs affichées à ce stade sont des tensions RMS brutes côté sortie capteur, pas
  encore des volts/ampères réels — la procédure de calibration (mesure de référence au
  multimètre puis calcul du coefficient) est documentée mais reste à exécuter.
- **Sécurité et logique de commande** : au démarrage, tous les relais sont forcés à l'état
  inactif avant même la configuration de la broche en sortie (évite un claquement parasite
  des relais actifs à l'état bas), et le système démarre en mode manuel. Un garde-fou local
  (seuils de puissance : 80 W par ligne, 120 W au total, sous un onduleur de 150 W) s'applique
  à toute décision automatique, qu'elle provienne d'une règle locale ou d'un backend distant.
  Des commandes série (`on/off 1|2|3`, `all on/off`, `auto`, `manual`, `status`) permettent un
  pilotage manuel pour les tests.
- **Statut de l'intégration réseau — à décrire avec prudence** : le firmware prévoit un mode
  automatique s'appuyant soit sur une logique locale simplifiée, soit sur un appel HTTP vers
  un backend distant. **Cette seconde voie n'est, à ce stade, reliée à aucune route existante
  du backend Django réel** : l'URL et le format de réponse attendus par le firmware sont un
  contrat provisoire propre au firmware, distinct de l'API de décision réellement exposée par
  le backend (voir section 4 ci-dessous pour le détail technique, à ne pas nécessairement
  développer dans le mémoire mais à ne jamais présenter comme déjà opérationnel). Le firmware
  est actuellement configuré en mode local (sans Wi-Fi), ce qui correspond à une phase de
  test du nœud IoT indépendamment du backend.

**Point à faire valider par l'auteur avant rédaction finale** : le mémoire ne doit affirmer
un test réussi (ex. « les relais ont cliqué », « la ligne 1 a bien commuté sous charge AC »)
que si ce résultat a été **effectivement observé et peut être décrit avec précision**
(date, comportement observé). D'après les éléments fournis, seul le **téléversement du
firmware sur la carte réelle a été confirmé** (message `Done uploading`, port COM3
identifié) ; le test fonctionnel des relais et des lignes AC n'est pas documenté avec un
résultat précis dans les échanges disponibles. Vérifie ce point avec l'auteur avant
d'écrire une phrase de type « le test a confirmé... ».

### 2.3 Chapitre 4.6 — API du backend (mise à jour de l'inventaire des routes)

Remplacer/compléter la liste des routes par l'inventaire suivant, vérifié dans le code
(à reformuler academiquement, en gardant les chemins exacts) :

**Mesures et appareils** (`apps/devices`, `apps/measurements`) :
- `GET/POST /api/houses/<house_id>/sensors/`
- `GET/POST /api/houses/<house_id>/equipment/`
- `GET/PUT/PATCH/DELETE /api/equipment/<pk>/`
- `GET/POST /api/measurements/` (création/liste/consultation uniquement, pas de
  modification/suppression)
- `GET /api/measurements/latest/?house=ID`
- `GET /api/measurements/history/`
- `POST /api/measurements/weather/collect/`, `GET /api/measurements/weather/status/`

**Prévision** (`apps/forecasting`) :
- `POST /api/forecasting/models/import/` (réservé à l'administrateur)
- `GET|POST /api/forecasting/predict/` (paramètres : `target`, `hours`, `step_minutes`
  — défaut 10 min —, `page`, `page_size` — max 288 —, `house`)
- `GET /api/forecasting/forecasts/`, `GET /api/forecasting/forecasts/latest/`
- `GET /api/forecasting/models/`, `PATCH /api/forecasting/models/{id}/` (administrateur)

**Décision** (`apps/fuzzy_engine`) :
- `GET /api/decisions/`, `GET /api/decisions/latest/`, `GET /api/decisions/{id}/`
- `POST /api/decisions/trigger/` (payload : `house`, `production_pv`, `consommation`,
  `batterie_soc`, `non_critiques_actives`)

**Rapports** (`apps/reports`) :
- `GET /api/reports/daily/?house=ID&date=YYYY-MM-DD`
- `GET /api/reports/summary/?house=ID&days=N` (ou `start`/`end`) — **route ajoutée
  récemment** : agrégation journalière de la production/consommation en kWh par intégration
  trapézoïdale des mesures de puissance, avec exclusion des intervalles de mesure supérieurs
  à 3 heures pour éviter de fabriquer de l'énergie fictive.
- `GET /api/reports/export/csv/?house=ID&type=measurements|forecasts|decisions|full`
- `GET /api/reports/exports/`, `GET /api/reports/exports/{id}/`

### 2.4 Chapitre 4.5 — Système expert flou (corrections factuelles importantes)

Le moteur réellement implémenté (`apps/fuzzy_engine/core/`) comprend **24 règles** (fonction
`get_default_rules()`), pas seulement les 7 exemples actuellement listés au tableau 7 du
chapitre 3.5 (méthodologie) et à la section 4.5.3. **Ne supprime pas les exemples existants**,
mais :
- précise que le tableau du chapitre 3 est un **extrait illustratif**, et que le moteur
  implémenté en compte 24 ;
- si tu ajoutes des exemples réels au chapitre 4, utilise des identifiants réellement
  présents dans le code, par exemple : `R001_BATTERY_TEMPERATURE_DANGEROUS`,
  `R003_BATTERY_SOC_CRITICAL`, `R005_CRITICAL_DEFICIT_NON_PRIORITY`,
  `R006_CRITICAL_DEFICIT_PRIORITY`, `R012_SURPLUS_CHARGE_BATTERY_LOW`,
  `R017_BAD_DATA_QUALITY`, `R021_NON_PRIORITY_LOAD_ECO_MODE`,
  `R023_CRITICAL_LOAD_PROTECTION`, `R024_SENSOR_DATA_ANOMALY` — ne renomme pas ces
  identifiants, ils sont réels.
- Les codes de décision réellement produits sont : `PROTECT_BATTERY`,
  `SHED_NON_PRIORITY_LOAD`, `RECOMMEND_REDUCE_PRIORITY_LOAD`, `USE_BATTERY`,
  `CHARGE_BATTERY`, `NORMAL_OPERATION`, `ECO_MODE`, `BLOCK_AUTOMATIC_ACTION`,
  `DATA_QUALITY_ALERT` — ceux-ci correspondent déjà bien au tableau 19 du mémoire actuel
  (à vérifier ligne par ligne, mais globalement cohérent).
- **Point à ajouter obligatoirement, avec nuance** : le moteur produit **une seule décision
  par maison/micro-réseau** (le modèle `Decision` n'a de clé étrangère que vers `House` et,
  optionnellement, vers une prévision). Il n'existe **aucune** granularité par ligne,
  canal de relais ou équipement individuel dans la décision produite. La priorité des
  charges (`load_priority`) est elle-même calculée comme le **pire cas agrégé** sur
  l'ensemble des équipements actifs de la maison, pas par ligne. Ce point doit être formulé
  clairement comme une limite architecturale actuelle (voir section 3 ci-dessous), sans
  quoi le lecteur pourrait croire que le système peut déjà produire une décision du type
  « ligne 1 ON, ligne 2 OFF, ligne 3 ON ».

### 2.5 Chapitre 4.4.7 / 4.9 — Cohérence modèle LSTM vs modèle réellement actif

Point de vigilance factuel à corriger ou nuancer : les métriques citées dans le mémoire pour
le LSTM (production photovoltaïque : MAE=25,787, RMSE=40,886, R²=0,825) et pour le GRU
(consommation : MAE=0,222, RMSE=0,361, R²=0,821) correspondent **exactement** aux fichiers
`best_model_info.json`/`metrics.json` du dépôt — ces chiffres sont corrects et peuvent rester
tels quels.

En revanche, pour la **production photovoltaïque uniquement**, le modèle réellement activé
dans la base de données via la commande d'enregistrement documentée (`register_models.py`)
n'est **pas** le LSTM mais un **Random Forest** (`ACTIVE_OVERRIDE` dans le code), avec la
justification déjà présente dans `metrics_rf.json` : un RMSE légèrement supérieur
(41,343 contre 40,886) mais une MAE, une MAPE et une précision à ±10 W nettement meilleures.
Deux options de rédaction, à choisir avec l'auteur :
- **Option A (recommandée si le prototype démontré utilise réellement le RF)** : présenter
  le LSTM comme le modèle retenu à l'issue de la comparaison expérimentale (meilleur RMSE),
  et le Random Forest comme le modèle **effectivement déployé/actif** dans le système
  implémenté, en expliquant le compromis (précision ponctuelle vs RMSE global). Ceci renforce
  la rigueur du mémoire plutôt que de l'affaiblir.
- **Option B** : si l'auteur confirme avoir exécuté `register_ml_models.py` (qui n'applique
  pas cet override et activerait bien le LSTM) pour la version démontrée, alors le texte
  actuel du mémoire reste correct tel quel, et il suffit d'ajouter une note de bas de page
  clarifiant qu'une commande d'enregistrement alternative applique un choix différent pour
  la production.

**Demander explicitement à l'auteur laquelle des deux commandes a servi à produire l'état
actif du système tel que démontré**, avant de trancher la rédaction.

### 2.6 Chapitre 4.6.4 — Retirer la mention du mécanisme de secours par profil horaire

Le texte actuel indique : *« Lorsqu'aucun modèle importé n'est disponible, le backend prévoit
un mécanisme de secours basé sur un profil horaire. »* Cette phrase **ne correspond plus au
code actuel** : le mécanisme de secours mathématique/profil a été retiré (le code documente
explicitement l'absence de repli et lève une erreur explicite en l'absence de modèle actif).
**Supprimer cette phrase** et la remplacer par une formulation du type :

> En l'absence de modèle actif pour une cible donnée, le système ne produit pas de prévision
> de repli : une erreur explicite est renvoyée, afin de ne jamais présenter à l'utilisateur
> une estimation non issue d'un modèle entraîné.

### 2.7 Chapitre 4.7 — Interface de supervision (précisions et corrections mineures)

- L'interface web comprend **13 pages** au total, dont 9 pages fonctionnelles EMS
  (tableau de bord, micro-réseaux, équipements, mesures, prévisions, décisions, alertes,
  rapports, paramètres) et 4 pages publiques/vitrine (accueil, tarification, connexion,
  inscription). La page de tarification (« Pricing ») est une page marketing statique sans
  lien avec la supervision énergétique ; si le mémoire ne la mentionne pas, ce n'est pas une
  erreur, mais il ne faut pas non plus prétendre décrire *exhaustivement* toutes les pages du
  frontend sans la citer au moins en une phrase.
- **Gestion des équipements** : sur le **web**, la page Équipements est actuellement en
  **lecture seule** (les fonctions de création/modification existent côté client API mais ne
  sont pas branchées à un formulaire dans l'interface). Sur le **mobile**, un formulaire de
  création d'équipement existe et fonctionne (nom, type, puissance nominale, priorité,
  statut) — les capteurs, eux, restent en lecture seule sur les deux plateformes. Le tableau
  10 du chapitre 3.7 (« Gestion des équipements ») doit préciser cette différence de
  couverture entre les deux interfaces plutôt que de la présenter comme uniformément
  disponible.
- Tous les appels API des deux interfaces (mobile et web) filtrent uniquement par `house` —
  aucune des deux ne permet de visualiser ou de piloter une ligne électrique individuelle,
  ce qui est cohérent avec l'absence de ce concept côté backend (voir 2.4).

### 2.8 Chapitre 4.8 — Intégration globale (reformulation nécessaire)

Le texte actuel (4.8.1 à 4.8.4) décrit un flux unique et déjà bouclé, de la mesure à la
décision puis à l'affichage. **Cette description reste correcte pour la chaîne logicielle
« maison entière »** (mesures → prévision → système expert → décision → interface), qui est
réellement fonctionnelle et déjà illustrée par les captures d'écran du mémoire. Il faut
cependant **ajouter une clarification explicite** indiquant que :

> Le prototype matériel ESP32 (section 4.6.7) constitue une brique complémentaire, développée
> et testée séparément. Son raccordement au flux logiciel décrit ci-dessus n'est, à ce stade,
> pas encore réalisé de bout en bout : l'ingestion de mesures génériques par maison (via API
> ou MQTT) et la commande physique des trois lignes du prototype sont deux chemins qui restent
> à unifier, notamment par l'introduction d'une notion de ligne/canal dans le modèle de
> données du backend et par l'alignement du protocole de communication du firmware sur les
> routes réellement exposées par l'API de décision.

Ne retire pas le scénario de test « de bout en bout » déjà décrit s'il correspond à un test
réel effectué sur la chaîne logicielle seule (sans le matériel) — précise simplement son
périmètre.

---

## 3. Points à présenter comme limites (chapitre « Limites », probablement 4.9.5 ou une
nouvelle sous-section dédiée)

- Absence de tout concept de « ligne » ou de « canal de relais » dans le modèle de données du
  backend (`Sensor`, `Equipment`, `Measurement`, `Decision`) : impossible aujourd'hui
  d'associer une mesure ou une décision à une ligne physique précise.
- Absence de canal de commande du backend vers l'ESP32 (aucune publication MQTT sortante,
  aucune route de pilotage de relais) : la chaîne de décision ne peut pas aujourd'hui
  déclencher une action physique.
- Contrat de communication HTTP entre le firmware et un backend distant non aligné sur l'API
  réelle (route et format de réponse fictifs côté firmware).
- Calibration des capteurs de tension/courant non réalisée (coefficients par défaut).
- Ambiguïté sur le modèle de prévision de production réellement actif selon la commande
  d'enregistrement exécutée (LSTM vs Random Forest) — à trancher (voir 2.5).
- Module `edge-gateway` fonctionnel en tant que code mais non intégré à la démonstration :
  déclaré uniquement sous un profil Docker optionnel, absent du déploiement de production,
  aucun producteur MQTT réel actuellement (le firmware ESP32 n'utilise pas MQTT), et le
  sélecteur de mode « Edge » de l'application mobile ne cible pas la véritable surface
  d'API de ce module par défaut.
- Gestion des équipements en lecture seule sur l'interface web (voir 2.7).

## 4. Points à présenter comme perspectives (chapitre « Perspectives »)

- Introduction d'une notion de ligne/circuit dans le modèle de données (`Equipment`,
  `Sensor`, éventuellement `Decision`) pour permettre une décision et une supervision par
  ligne, cohérente avec le prototype physique à 3 lignes.
- Développement d'un mécanisme de commande du backend vers l'ESP32 (nouvelle route API dédiée
  au pilotage de relais, ou publication MQTT sortante), pour fermer la boucle
  capteurs → décision → actionneurs.
- Adaptation du firmware pour consommer l'API de décision réellement exposée
  (`/api/decisions/trigger/`) plutôt que le contrat provisoire actuel, avec une couche de
  traduction décision-maison → état par ligne.
- Calibration métrologique complète des capteurs ZMPT101B/ZMCT103C.
- Intégration effective du module `edge-gateway` dans le flux de données (le firmware
  publiant réellement en MQTT), avec tests de bout en bout du mode dégradé hors ligne.
- Selon le contexte académique, une mention **courte** de l'intérêt d'un système expert plus
  adaptatif (apprentissage des règles) ou d'un assistant conversationnel pour l'exploitation
  du système peut être ajoutée ici — jamais présentée comme déjà implémentée.

---

## 5. Sections du chapitre 3 (Méthodologie) à signaler pour révision ultérieure

*(L'auteur a indiqué que la méthodologie sera précisée dans un temps séparé — se limiter ici
à signaler les sections concernées, sans les réécrire.)*

- **3.1 / 2.1.5** — la description de l'architecture Edge-Cloud et du protocole MQTT comme
  déjà en usage entre l'ESP32 et le backend est à nuancer : le firmware actuel n'utilise pas
  MQTT et le module edge-gateway n'est pas intégré à la démonstration.
- **3.2.4 / 3.2.5 / 3.2.6** — les diagrammes de séquence « collecte des données IoT » et de
  déploiement représentent un flux ESP32 → MQTT → backend qui n'a, à ce jour, aucun
  producteur réel côté firmware.
- **3.5 (tableau 7)** — extrait de règles floues à recontextualiser comme un sous-ensemble
  pédagogique du moteur réel (24 règles).
- **3.7 (tableau 10)** — à harmoniser avec la différence de couverture web/mobile pour la
  gestion des équipements.

---

## 6. Tableaux à créer ou mettre à jour

1. **Tableau des composants matériels** : panneau solaire, régulateur de charge, batteries
   12 V, onduleur 12 V DC → 220 V AC, module relais 8 canaux (3 utilisés), capteurs ZMPT101B
   ×3, capteurs ZMCT103C ×3, ESP32 DevKit, charges (lampes 10/10/20 W, 2 prises).
2. **Tableau des broches ESP32** : GPIO25/26/27 (relais, IN1/IN3/IN6) ; GPIO34/35/32/33/36(SP)/39(SN)
   (capteurs) ; mention explicite des broches interdites (CMD, SD0-3, CLK) et des broches
   entrée-seule (34, 35, 36, 39).
3. **Tableau des lignes électriques** : ligne, canal relais, charges, capteur tension, capteur
   courant, priorité fonctionnelle de démonstration (ligne 2 = non prioritaire, ligne 3 =
   prioritaire).
4. **Tableau de correspondance relais/lignes** (COM/NO utilisés, NC non utilisé).
5. **Tableau de correspondance capteurs/lignes** (déjà couvert par 3, peut être fusionné).
6. **Tableau des règles du système expert** : mettre à jour ou compléter avec les identifiants
   réels listés en 2.4, en indiquant qu'il s'agit d'un extrait sur 24 règles.
7. **Tableau des tests réalisés** — à remplir uniquement avec des tests confirmés :
   - Compilation/téléversement du firmware sur ESP32 réel : **réalisé** (COM3, message
     `Done uploading`).
   - Test de commutation des relais sans charge AC : **statut à confirmer avec l'auteur**
     avant de l'écrire comme réalisé.
   - Test des lignes AC sous charge réelle : **à confirmer / probablement non réalisé à ce
     jour**.
   - Déclenchement du système expert et affichage de la décision (chaîne logicielle) :
     **réalisé**, illustré par les captures d'écran déjà présentes au chapitre 4.
   - Intégration réseau ESP32 ↔ backend Django : **non réalisée** (`USE_WIFI=0`, contrat HTTP
     non aligné sur l'API réelle).
8. **Tableau des limites et améliorations futures** : reprendre les points des sections 3 et 4
   ci-dessus sous forme synthétique (limite / cause / amélioration proposée).

## 7. Figures à ajouter ou corriger

- **Schéma de câblage des trois lignes AC** (onduleur → répartition du conducteur contrôlé →
  3 canaux de relais → capteurs → charges), fidèle à la description matérielle réelle.
- **Schéma ESP32 – relais – capteurs** avec les références de broches exactes.
- **Diagramme de flux révisé** distinguant clairement, par un code couleur ou un cadre en
  pointillés, ce qui est aujourd'hui *opérationnel de bout en bout* (chaîne logicielle maison
  entière) de ce qui est *prévu mais non encore raccordé* (boucle ESP32 ↔ backend). Ce
  diagramme est probablement la correction visuelle la plus importante à apporter, car les
  diagrammes actuels (contexte, séquences, déploiement) laissent penser que la boucle
  matérielle est déjà fermée.
- Éventuellement un schéma d'ensemble du prototype physique (panneau → régulateur → batterie
  → onduleur → répartition → relais → lignes) à visée pédagogique, sans donner de valeurs
  électriques non mesurées.

## 8. Fichiers du dépôt à consulter pour rédiger ces sections

Backend :
- `ems-backend/apps/devices/models.py`, `serializers.py`, `views.py`, `urls.py`
- `ems-backend/apps/measurements/models.py`, `services.py`, `views.py`, `urls.py`
- `ems-backend/apps/mqtt_handler/handlers.py`, `management/commands/run_mqtt.py`
- `ems-backend/apps/fuzzy_engine/core/{models,facts,membership,rules,inference,defuzzification,decision_mapper,engine}.py`
- `ems-backend/apps/fuzzy_engine/{models.py,engine.py,views.py,urls.py,serializers.py}`
- `ems-backend/apps/forecasting/{models.py,services.py,views.py,urls.py}`
- `ems-backend/apps/forecasting/management/commands/{register_models.py,register_ml_models.py}`
- `ems-backend/apps/reports/{models.py,views.py,urls.py,serializers.py}`
- `ems-backend/ml_models/production/{best_model_info.json,metrics.json,metrics_rf.json}`
- `ems-backend/ml_models/consumption/{best_model_info.json,metrics.json}`

Firmware :
- `esp32-firmware/platformio.ini`, `esp32-firmware/include/config.h`,
  `esp32-firmware/src/main.cpp`, `esp32-firmware/README.md`

Mobile :
- `ems-mobile/src/screens/{DashboardScreen,HistoryScreen,DecisionsScreen,DecisionDetailScreen,ReportsScreen,DevicesScreen,AlertsScreen}.js`
- `ems-mobile/src/api/endpoints.js`

Web :
- `ems-frontend/src/pages/{Dashboard,Houses,Devices,Measurements,Forecasting,Decisions,Alerts,Reports,Settings,Pricing,Landing,Login,Register}.jsx`
- `ems-frontend/src/App.jsx`, `ems-frontend/src/api/endpoints.js`

Edge-gateway :
- `edge-gateway/{local_cache.py,mqtt_subscriber.py,sync_service.py,Dockerfile,README.md}`
- `docker-compose.yml`, `docker-compose.prod.yml` (pour vérifier le profil `edge`)

---

## 9. Précautions finales avant de rédiger

- Ne jamais transformer un « contrat prévu par le firmware » en « fonctionnalité du
  backend » : ce sont deux choses différentes tant que la route `/api/ems/decision/` n'existe
  pas côté Django.
- Ne jamais affirmer qu'une décision par ligne est produite par le système expert : à ce jour,
  une seule décision par maison est produite.
- Ne jamais présenter l'edge-gateway comme intégré à la démonstration.
- Toujours vérifier auprès de l'auteur le résultat réel des tests physiques (relais, lignes
  AC) avant de les décrire comme réussis.
- Sur le choix de modèle de prévision de production (LSTM vs RF), demander confirmation à
  l'auteur avant de trancher la rédaction (voir 2.5).

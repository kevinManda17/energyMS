# Diagrammes du système EMS

Onze diagrammes décrivant la plateforme **telle qu'elle est aujourd'hui**, sur la
branche `refonte-delestage`. Ils remplacent les neuf diagrammes précédents, qui
décrivaient un système d'avant trois refontes : la ligne n'y était pas une
entité, l'autonomie y figurait comme un fait du moteur, et un optimiseur y
tenait la place que le plan de délestage occupe désormais.

## Ce qui est où

| Diagramme | Type | Format | Ce qu'il montre |
|---|---|---|---|
| `erd_complet` | ERD | paysage 6217×5113 | **Les 25 tables du domaine**, toutes leurs colonnes, les 31 relations avec leur cardinalité et leur comportement à la suppression |
| `cas_utilisation` | cas d'utilisation | 1719×1483 | Les six acteurs — dont quatre non humains — et ce que chacun déclenche |
| `classes_systeme_expert` | classes | paysage 3048×1778 | Le noyau flou : faits, règles, inférence, conclusions. Aucune dépendance Django |
| `classes_chaine_iot` | classes | 2025×2185 | Le code qui va du capteur au relais — ce que l'ERD ne montre pas |
| `classes_prevision` | classes | 1640×1496 | Les trois chemins de prédiction et pourquoi ils diffèrent |
| `sequence_boucle_fermee` | séquence | portrait 1676×2953 | Un sondage ESP32 de bout en bout, avec les trois cadences 3 s / 30 s / 180 s |
| `sequence_decision_experte` | séquence | portrait 2098×3318 | Le raisonnement en quatre étapes, en mémoire, sans une requête |
| `sequence_prevision` | séquence | portrait 1305×2262 | Déroulé autorégressif GRU contre prédiction en lot |
| `activite_cascade_decision` | activité | paysage 2330×1241 | La cascade et ses neuf issues — l'ordre des tests EST la décision |
| `activite_plan_delestage` | activité | 2184×1922 | Comment le moteur construit sa commande de lignes |
| `activite_estimation_soc` | activité | paysage 1853×1416 | L'arbitrage entre BMS, tension au repos et comptage — et les quatre refus |

Chaque diagramme existe en **SVG** (vectoriel, à privilégier) et en **PNG**
(140 dpi). L'ERD existe aussi en **PDF**, format le plus commode pour une
planche dépliante.

`sources/` contient les fichiers d'origine : `.puml` pour les diagrammes UML,
`.dot` pour l'ERD.

## L'ERD n'est pas dessiné, il est extrait

`ems-backend/tools/generer_erd.py` lit le registre des modèles Django et produit
le `.dot`. C'est délibéré : un ERD recopié à la main devient faux le jour où une
migration passe, et personne ne s'en aperçoit — le dessin ne casse pas, il ment.
Celui-ci décrit le schéma tel qu'il est au moment où on l'exécute.

C'est aussi la seule façon de tenir la promesse « tout le schéma » : vingt-cinq
tables et une centaine de colonnes ne se recopient pas sans en oublier.

Le générateur **échoue bruyamment** si aucune table n'est trouvée. Un schéma vide
se dessine très bien : Graphviz produit un cadre soigné, sans erreur, et l'on
croit avoir un ERD. C'est exactement ce qui est arrivé au premier essai, parce
que `config.settings` est un paquet dont l'`__init__` est vide — Django démarrait
alors avec `INSTALLED_APPS` vide, sans le moindre avertissement.

### Notation de l'ERD

| Symbole | Sens |
|---|---|
| `PK` / `FK` | clé primaire / clé étrangère |
| `?` | colonne nullable |
| `∪` | valeur unique |
| `⚿` | contrainte multi-colonnes — c'est là que vivent les règles métier |
| trait plein / tireté | suppression en cascade / mise à `NULL` |

Les contraintes multi-colonnes méritent d'être lues : `une_mesure_par_grandeur_et_instant`,
`un_releve_par_ligne_et_instant`, `ligne_unique_par_maison`,
`mesure_capteur_a_un_capteur`. Ce sont elles qui empêchent deux collectes
concurrentes d'écrire des valeurs contradictoires, et une estimation de se faire
passer pour une lecture de capteur.

## Régénérer

```bash
cd docs/diagrams && ./regenerer.sh
```

Nécessite `plantuml` et `graphviz`, tous deux déjà installés sur le poste.
Aucun accès réseau n'est requis : tout est rendu localement.

L'ERD se met à jour tout seul à chaque exécution. Les diagrammes UML, eux, sont
écrits à la main : le script les **recompile**, il ne les met pas à jour. Après
une modification du noyau expert ou de la chaîne IoT, il faut relire les `.puml`.

## Inclure dans le mémoire

Le SVG est vectoriel : il reste net à n'importe quel agrandissement, ce qui
compte pour l'ERD.

```latex
% Diagramme au format page, en paysage
\begin{figure}[p]
  \centering
  \includegraphics[width=\textwidth]{figures/diagrammes/activite_plan_delestage.pdf}
  \caption{Construction du plan de délestage.}
  \label{fig:plan-delestage}
\end{figure}

% L'ERD complet, en planche dépliante
\begin{sidewaysfigure}[p]
  \centering
  \includegraphics[width=\textheight]{figures/diagrammes/erd_complet.pdf}
  \caption{Schéma relationnel complet — 25 tables.}
\end{sidewaysfigure}
```

`pdflatex` ne lit pas le SVG. Deux voies :

- convertir une fois pour toutes : `inkscape --export-type=pdf fichier.svg`
  (Inkscape n'est pas installé sur le poste) ou `rsvg-convert -f pdf` ;
- ou simplement inclure les PNG, qui sont à 140 dpi — suffisant pour les
  diagrammes UML, un peu juste pour l'ERD si on l'imprime en A4.

L'ERD est déjà fourni en PDF vectoriel, ce qui règle le cas le plus exigeant.

## Ce que ces diagrammes ne montrent pas

À signaler plutôt qu'à laisser découvrir :

- **Les tables techniques de Django** (`auth_*`, `django_session`,
  `django_migrations`, `django_admin_log`) sont exclues de l'ERD. Elles
  appartiennent au cadre, pas au domaine.
- **`RelayState` figure encore** dans l'ERD et dans le diagramme de la chaîne
  IoT. Elle est remplacée par `Line` + `LineState` + `IoTNode` depuis la refonte
  de la base, mais elle n'a pas été supprimée : le firmware déployé sonde encore
  par son jeton, et un nœud sur le terrain ne se reflashe pas à distance. Les
  deux coexistent, et le dessin le montre plutôt que de le masquer.
- **Le champ `unit` de `Measurement`** subsiste à côté de `quantity`, de même que
  `measurement_type`. Ce sont des colonnes de transition, conservées le temps que
  tous les lecteurs basculent.
- **Les interfaces web et mobile** ne sont pas diagrammées : elles consomment
  l'API décrite ici, sans logique propre qui mériterait un diagramme.
- **Le firmware ESP32 et la passerelle Edge** apparaissent comme acteurs, jamais
  comme structure interne : ils n'ont pas été modifiés et ne relèvent pas de ce
  dépôt.

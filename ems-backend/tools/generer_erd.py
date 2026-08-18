"""
Le schéma relationnel, extrait de Django plutôt que dessiné à la main.

    cd ems-backend
    python -m tools.generer_erd > ../docs/diagrams/sources/erd_complet.dot

POURQUOI L'EXTRAIRE ET NON LE DESSINER

Un ERD recopié à la main est faux le jour où une migration passe, et personne
ne s'en aperçoit : le dessin ne casse pas, il ment. Celui-ci lit le registre
des modèles au moment où on l'exécute. S'il affiche une colonne, c'est qu'elle
existe ; s'il en manque une, c'est qu'elle n'existe plus.

C'est aussi la seule façon de tenir la promesse « tout le schéma » : vingt-cinq
tables et une centaine de colonnes ne se recopient pas sans en oublier.

CE QUE LE DESSIN MONTRE, ET CE QU'IL TAIT

Montré : chaque table avec ses colonnes typées, la clé primaire, les clés
étrangères, les colonnes nullables, les contraintes d'unicité multi-colonnes
(ce sont elles qui portent les règles métier : une ligne par maison, une mesure
par grandeur et par instant), et les relations avec leur cardinalité.

Tu : les index de performance, qui ne disent rien du modèle, et les tables
techniques de Django (sessions, permissions, migrations) qui appartiennent au
cadre et non au domaine.
"""
from __future__ import annotations

import os
import sys

import django

# Applications du DOMAINE. Les tables de Django (auth, admin, sessions,
# contenttypes) sont exclues : elles décrivent le cadre, pas le micro-réseau.
APPS_DOMAINE = [
    ("users", "Comptes et vérifications", "#E8EAF6", "#3F51B5"),
    ("houses", "Micro-réseau", "#E0F2F1", "#00796B"),
    ("energy_assets", "Actifs énergétiques", "#FFF3E0", "#E65100"),
    ("devices", "Lignes, nœuds et capteurs", "#E3F2FD", "#1565C0"),
    ("measurements", "Mesures et agrégats", "#F1F8E9", "#558B2F"),
    ("forecasting", "Prévision", "#FCE4EC", "#AD1457"),
    ("fuzzy_engine", "Système expert", "#F3E5F5", "#6A1B9A"),
    ("alerts", "Alertes", "#FFF8E1", "#F9A825"),
    ("datasets", "Jeux de données", "#EFEBE9", "#5D4037"),
    ("reports", "Exports", "#ECEFF1", "#455A64"),
]

# Types Django ramenés à leur nature relationnelle. Un `CharField(choices=…)`
# reste un texte en base : afficher « énumération » ferait croire à un type SQL
# qui n'existe pas dans SQLite ni dans PostgreSQL tel qu'on l'utilise ici.
TYPES = {
    "AutoField": "int", "BigAutoField": "int", "IntegerField": "int",
    "PositiveIntegerField": "int+", "PositiveSmallIntegerField": "int+",
    "SmallIntegerField": "int", "FloatField": "float",
    "BooleanField": "bool", "CharField": "texte", "TextField": "texte long",
    "EmailField": "courriel", "DateTimeField": "horodatage",
    "DateField": "date", "JSONField": "json", "FileField": "fichier",
    "ForeignKey": "fk", "OneToOneField": "fk unique",
    "DecimalField": "décimal", "URLField": "url",
}


def echapper(texte: str) -> str:
    """Graphviz lit du HTML dans les étiquettes : les chevrons doivent fuir."""
    return (str(texte).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def type_lisible(champ) -> str:
    nom = type(champ).__name__
    base = TYPES.get(nom, nom.replace("Field", "").lower())
    longueur = getattr(champ, "max_length", None)
    if longueur and base in ("texte", "courriel", "url"):
        return f"{base}({longueur})"
    return base


def contraintes_uniques(modele) -> list[str]:
    """Les contraintes multi-colonnes — celles qui portent une règle métier.

    `unique=True` sur une colonne isolée est déjà signalé dans la ligne du
    champ ; le répéter ici encombrerait sans rien apprendre.
    """
    lignes = []
    for contrainte in modele._meta.constraints:
        champs = getattr(contrainte, "fields", None)
        if champs and len(champs) > 1:
            lignes.append(f"unique({', '.join(champs)})")
        elif getattr(contrainte, "check", None) is not None:
            lignes.append(f"vérif. {contrainte.name}")
    for ensemble in modele._meta.unique_together:
        lignes.append(f"unique({', '.join(ensemble)})")
    return lignes


def table(modele, couleur_bord: str) -> str:
    meta = modele._meta
    nom_table = meta.db_table
    lignes = [
        f'  "{nom_table}" [label=<',
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">',
        f'<TR><TD BGCOLOR="{couleur_bord}" COLSPAN="3">'
        f'<FONT COLOR="white"><B>{echapper(nom_table)}</B></FONT></TD></TR>',
    ]

    for champ in meta.get_fields():
        if not getattr(champ, "concrete", False):
            continue          # relations inverses : portées par l'autre table
        if champ.many_to_many:
            continue

        marque, style_ouvert, style_ferme = "", "", ""
        if champ.primary_key:
            marque, style_ouvert, style_ferme = "PK", "<B>", "</B>"
        elif champ.is_relation:
            marque = "FK"

        nom = echapper(champ.name)
        if champ.is_relation:
            nom += " →"

        # Nullable : signalé par « ? ». C'est une information de modélisation,
        # pas de présentation — une colonne qui accepte NULL autorise un état
        # que le code doit traiter.
        suffixe = "?" if champ.null else ""
        if getattr(champ, "unique", False) and not champ.primary_key:
            suffixe += " ∪"

        # Graphviz 2.43 refuse un élément <FONT> sans contenu : la cellule est
        # donc laissée nue quand il n'y a pas de marque à porter.
        cellule_marque = (
            f'<FONT POINT-SIZE="9" COLOR="#B71C1C"><B>{marque}</B></FONT>'
            if marque else ""
        )
        lignes.append(
            f'<TR><TD ALIGN="LEFT" WIDTH="26">{cellule_marque}</TD>'
            f'<TD ALIGN="LEFT">{style_ouvert}{nom}{style_ferme}</TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="#546E7A">'
            f'{echapper(type_lisible(champ))}{echapper(suffixe)}</FONT></TD></TR>'
        )

    for contrainte in contraintes_uniques(modele):
        lignes.append(
            f'<TR><TD COLSPAN="3" ALIGN="LEFT" BGCOLOR="#FAFAFA">'
            f'<FONT POINT-SIZE="9" COLOR="#B71C1C">⚿ '
            f'{echapper(contrainte)}</FONT></TD></TR>'
        )

    lignes.append("</TABLE>>];")
    return "\n".join(lignes)


def relations(modeles) -> list[str]:
    """Les arêtes, avec leur cardinalité et le comportement à la suppression.

    `on_delete` figure sur l'arête parce qu'il fait partie du modèle : CASCADE
    et SET_NULL ne décrivent pas la même dépendance. Une mesure survit à son
    capteur (SET_NULL) ; un relevé de ligne ne survit pas à sa ligne (CASCADE).
    """
    connus = {m._meta.db_table for m in modeles}
    aretes = []
    for modele in modeles:
        for champ in modele._meta.get_fields():
            if not getattr(champ, "concrete", False) or not champ.is_relation:
                continue
            cible = champ.related_model._meta.db_table
            if cible not in connus:
                continue

            suppression = getattr(champ.remote_field, "on_delete", None)
            nom_suppression = getattr(suppression, "__name__", "")
            style = "dashed" if nom_suppression == "SET_NULL" else "solid"
            # « 1 » côté cible, « n » côté source : une maison a n lignes.
            # OneToOne fait exception, et c'est justement ce qui contraint le
            # modèle — d'où l'annotation distincte.
            cardinalite = "1" if champ.one_to_one else "n"
            aretes.append(
                f'  "{cible}" -> "{modele._meta.db_table}" '
                f'[taillabel="1", headlabel="{cardinalite}", '
                f'label=<<FONT POINT-SIZE="8" COLOR="#78909C">'
                f'{champ.name}<BR/>{nom_suppression.lower()}</FONT>>, '
                f'style={style}];'
            )
    return aretes


def legende() -> str:
    """Sans encadrés, la couleur d'en-tête devient la seule marque
    d'appartenance : il faut alors dire ce qu'elle signifie.

    Elle rappelle aussi la notation des colonnes — un « ? » ou un « ∪ » que le
    lecteur doit deviner ne transmet rien.
    """
    lignes = [
        '  "legende" [label=<',
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">',
        '<TR><TD BGCOLOR="#37474F" COLSPAN="2">'
        '<FONT COLOR="white"><B>Légende</B></FONT></TD></TR>',
    ]
    for _, titre, _, bord in APPS_DOMAINE:
        lignes.append(
            f'<TR><TD BGCOLOR="{bord}" WIDTH="18"> </TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10">{echapper(titre)}'
            f'</FONT></TD></TR>'
        )
    for symbole, sens in (
        ("PK", "clé primaire"),
        ("FK", "clé étrangère"),
        ("?", "colonne nullable"),
        ("∪", "valeur unique"),
        ("⚿", "contrainte multi-colonnes"),
        ("— / - -", "suppression en cascade / mise à NULL"),
    ):
        lignes.append(
            f'<TR><TD ALIGN="RIGHT"><FONT POINT-SIZE="10" COLOR="#B71C1C">'
            f'<B>{echapper(symbole)}</B></FONT></TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10">{echapper(sens)}'
            f'</FONT></TD></TR>'
        )
    lignes.append("</TABLE>>];")
    return "\n".join(lignes)


def main() -> int:
    # `config.settings` est un PAQUET, pas un module : son `__init__` est vide.
    # Le désigner laisse Django démarrer avec INSTALLED_APPS vide et sortir un
    # schéma sans aucune table — sans la moindre erreur. C'est exactement le
    # genre de silence contre lequel ce script existe : on prend donc le même
    # module que `manage.py`, et rien d'autre.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()
    from django.apps import apps as registre

    sortie = [
        "// ERD du micro-réseau — ENGENDRÉ par tools/generer_erd.py.",
        "// Ne pas modifier à la main : la prochaine exécution l'écraserait,",
        "// et une correction manuelle serait perdue sans laisser de trace.",
        "digraph erd {",
        # `splines=ortho` donnait des angles droits agréables mais Graphviz
        # refuse alors d'étiqueter les arêtes : on perdait le nom du champ et
        # le comportement à la suppression, c'est-à-dire l'essentiel de ce
        # qu'une relation a à dire. Les courbes gardent l'information.
        '  graph [rankdir=TB, splines=spline, nodesep=0.6, ranksep=1.2,',
        '         fontname="Helvetica", bgcolor="white", pad=0.4,',
        '         label=<<B>Schéma relationnel de la plateforme EMS</B>>,',
        '         labelloc=t, fontsize=20];',
        '  node [shape=plaintext, fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=9, color="#90A4AE",',
        '        arrowhead=crow, arrowtail=none, dir=both, penwidth=1.1];',
        "",
    ]

    # Les encadrés de groupe SONT une contrainte de placement : `houses_house`
    # est relié à dix tables réparties dans huit applications, et enfermer
    # chacune dans sa boîte oblige Graphviz à étirer la planche sur 4 250 pt
    # avec des arêtes qui la traversent de part en part. Sans les encadrés, le
    # placement suit les relations — ce qu'un ERD doit montrer — et la couleur
    # d'en-tête suffit à dire à quelle application chaque table appartient.
    groupes = "--groupes" in sys.argv

    tous = []
    for etiquette, titre, fond, bord in APPS_DOMAINE:
        try:
            config = registre.get_app_config(etiquette)
        except LookupError:
            continue
        modeles = list(config.get_models())
        if not modeles:
            continue
        tous.extend(modeles)
        if groupes:
            sortie.append(f'  subgraph "cluster_{etiquette}" {{')
            sortie.append(f'    label=<<B>{echapper(titre)}</B>>;')
            sortie.append(f'    style="rounded,filled"; fillcolor="{fond}";')
            sortie.append(f'    color="{bord}"; fontcolor="{bord}"; fontsize=14;')
            sortie.append("    margin=14;")
        for modele in modeles:
            sortie.append(table(modele, bord))
        if groupes:
            sortie.append("  }")
        sortie.append("")

    if not groupes:
        sortie.append(legende())
    sortie.extend(relations(tous))
    sortie.append("}")

    # Un schéma vide se dessine très bien : Graphviz produit un cadre soigné,
    # sans erreur, et l'on croit avoir un ERD. Mieux vaut échouer bruyamment.
    if not tous:
        print("ERREUR : aucune table trouvée. Les applications du domaine "
              "sont-elles chargées ? (DJANGO_SETTINGS_MODULE)", file=sys.stderr)
        return 1

    print("\n".join(sortie))
    print(f"// {len(tous)} tables du domaine", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

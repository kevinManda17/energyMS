"""Migre `measurement_type` + `unit` vers `quantity` + `source` (§2.4).

C'EST L'ETAPE OU UNE ERREUR D'UN FACTEUR MILLE EST POSSIBLE. Le depot en porte
deja la cicatrice : le backend a stocke des watts sous l'unite « kW » pendant
des mois, si bien que 40 W devenaient « 40 kW ». Chaque conversion ci-dessous
est donc explicite, et un test verifie qu'aucune valeur ne change d'ordre de
grandeur au-dela du facteur declare.

DEUX SUBTILITES

1. Plusieurs anciens types tombent sur la MEME grandeur au meme instant.
   `_store_line_measurements` ecrit `power` (W) ET `consumption` (kW) pour la
   meme puissance ; `_store_dc_measurements` ecrit `pv_power` (W) ET
   `production` (kW). Comme la nouvelle contrainte n'autorise qu'une valeur par
   (maison, grandeur, instant), il faut choisir.

   On garde la ligne NATIVE en watts plutot que celle en kilowatts. Raison
   mesurable : `consumption` vaut `round(power / 1000, 4)`, donc la reconvertir
   en watts ne rend que 0,1 W de granularite — on perdrait de la precision en
   repassant par l'unite derivee.

2. L'historique anterieur au 19/07/2026 contient des consommations fausses d'un
   facteur 1000 (documente dans MEASUREMENTS_UNITS.md §3). Ces lignes ne sont
   PAS corrigees ici : rien ne permet de les distinguer apres coup des valeurs
   deja justes. Les « corriger » reviendrait a fausser celles qui ne l'etaient
   pas. La conversion appliquee est celle de l'unite DECLAREE, sans exception.

Les types sans correspondance connue (`luminosity`, `reactive_power`,
`sub_metering_*`) gardent `quantity` vide : on ne leur invente pas une grandeur.
La contrainte d'unicite les tolere explicitement.
"""
from django.db import migrations


# (ancien type) -> (grandeur, facteur, provenance, priorite en cas de collision)
#
# `facteur` convertit la valeur stockee vers l'unite portee par le nom de la
# grandeur. `priorite` departage deux anciens types qui visent la meme grandeur
# au meme instant : le plus haut gagne.
CORRESPONDANCE = {
    # --- Puissances : la ligne native en W l'emporte sur la derivee en kW ----
    "power":            ("load_power_w",      1.0,    "DERIVED",     10),
    "consumption":      ("load_power_w",      1000.0, "DERIVED",      5),
    "pv_power":         ("pv_power_w",        1.0,    "SENSOR",      10),
    "production":       ("pv_power_w",        1000.0, "DERIVED",      5),
    # --- Reseau alternatif --------------------------------------------------
    "voltage":          ("grid_voltage_v",    1.0,    "DERIVED",     10),
    "current":          ("grid_current_a",    1.0,    "DERIVED",     10),
    # --- Batterie -----------------------------------------------------------
    "battery_soc":      ("battery_soc_pct",   1.0,    "DERIVED",     10),
    "battery_voltage":  ("battery_voltage_v", 1.0,    "SENSOR",      10),
    "battery_current":  ("battery_current_a", 1.0,    "SENSOR",      10),
    "battery_power":    ("battery_power_w",   1.0,    "DERIVED",     10),
    "battery_temp":     ("battery_temp_c",    1.0,    "SENSOR",      10),
    # --- Photovoltaique -----------------------------------------------------
    "pv_voltage":       ("pv_voltage_v",      1.0,    "SENSOR",      10),
    "pv_current":       ("pv_current_a",      1.0,    "SENSOR",      10),
    # `panel_temp` est une sonde posee sur le panneau, `module_temp` vient du
    # jeu de donnees d'entrainement. Meme grandeur physique : la sonde prime.
    "panel_temp":       ("module_temp_c",     1.0,    "SENSOR",      10),
    "module_temp":      ("module_temp_c",     1.0,    "DERIVED",      5),
    # --- Meteo : ESTIMEE, jamais mesuree ------------------------------------
    # C'est ce champ qui empechera la regle R032 de diagnostiquer une panne
    # photovoltaique sur la foi d'une irradiance qu'aucun capteur n'a lue.
    "temperature":       ("ambient_temp_c",         1.0, "WEATHER_API", 10),
    "irradiance":        ("irradiance_wm2",         1.0, "WEATHER_API", 10),
    "irradiance_tilt15": ("irradiance_tilt15_wm2",  1.0, "WEATHER_API", 10),
    "irradiance_tilt20": ("irradiance_tilt20_wm2",  1.0, "WEATHER_API", 10),
    "irradiance_east":   ("irradiance_east_wm2",    1.0, "WEATHER_API", 10),
    "irradiance_west":   ("irradiance_west_wm2",    1.0, "WEATHER_API", 10),
    "humidity":          ("humidity_pct",           1.0, "WEATHER_API", 10),
    "wind_speed":        ("wind_speed_ms",          1.0, "WEATHER_API", 10),
    "wind_direction":    ("wind_direction_deg",     1.0, "WEATHER_API", 10),
    "air_pressure":      ("air_pressure_hpa",       1.0, "WEATHER_API", 10),
}

# Types volontairement NON migres, faute de grandeur correspondante. Ils
# viennent du jeu de donnees public d'entrainement et n'ont pas d'equivalent
# physique dans ce micro-reseau. Leur inventer une grandeur serait pire que de
# les laisser tels quels.
SANS_CORRESPONDANCE = (
    "luminosity", "reactive_power",
    "sub_metering_1", "sub_metering_2", "sub_metering_3",
)


def migrer(apps, schema_editor):
    """Convertit en DEUX temps, et dans cet ordre.

    Les collisions sont resolues AVANT d'ecrire quoi que ce soit. Ecrire
    d'abord et deduplique ensuite ne fonctionnerait que tant que la contrainte
    d'unicite n'existe pas encore — ce qui est vrai aujourd'hui (elle arrive en
    0011), mais rend la migration dependante de son rang. Une migration ne doit
    pas reposer sur ce qui ne s'est pas encore produit.
    """
    Measurement = apps.get_model("measurements", "Measurement")
    _supprimer_doublons(Measurement)
    _convertir(Measurement)


def _supprimer_doublons(Measurement):
    """Ne garde qu'une ligne par (maison, grandeur visee, instant).

    Deux anciens types decrivant la meme grandeur au meme instant existent
    reellement : `power`/`consumption` et `pv_power`/`production` sont ecrits
    ENSEMBLE par le meme code, la meme puissance dans deux unites.

    On conserve la plus prioritaire — celle dont l'unite d'origine est NATIVE,
    donc celle qui n'a pas transite par une division suivie d'une
    multiplication. `consumption` vaut `round(power / 1000, 4)` : la
    reconvertir ne rendrait que 0,1 W de granularite.
    """
    vus: dict[tuple, tuple[int, int]] = {}
    a_supprimer: list[int] = []

    champs = ("id", "house_id", "timestamp", "measurement_type")
    for pk, house_id, instant, ancien in (
        Measurement.objects.filter(measurement_type__in=list(CORRESPONDANCE))
        .order_by("id")
        .values_list(*champs)
        .iterator(chunk_size=2000)
    ):
        grandeur, _facteur, _provenance, priorite = CORRESPONDANCE[ancien]
        cle = (house_id, grandeur, instant)
        precedent = vus.get(cle)
        if precedent is None:
            vus[cle] = (pk, priorite)
        elif priorite > precedent[1]:
            a_supprimer.append(precedent[0])
            vus[cle] = (pk, priorite)
        else:
            a_supprimer.append(pk)

    if a_supprimer:
        Measurement.objects.filter(id__in=a_supprimer).delete()


def _convertir(Measurement):
    """Applique la grandeur, le facteur et la provenance.

    LA PROVENANCE SE DEDUIT DU CAPTEUR, pas seulement du type :

      - une ligne rattachee a un capteur EST une lecture de capteur, quelle que
        soit la provenance par defaut de son type ;
      - une ligne dont le type est repute mesure mais qui ne NOMME aucun
        capteur retombe sur DERIVED. C'est exactement ce que dit la contrainte
        `mesure_capteur_a_un_capteur` : une donnee qui ne peut pas designer son
        capteur ne peut pas se reclamer d'une mesure. L'historique en contient
        — les grandeurs continues ont ete ecrites avant que les capteurs du
        noeud secondaire ne soient enregistres.
    """
    for ancien, (grandeur, facteur, provenance, _prio) in CORRESPONDANCE.items():
        lignes = Measurement.objects.filter(measurement_type=ancien).exclude(
            quantity=grandeur
        )
        for ligne in lignes.iterator(chunk_size=2000):
            ligne.quantity = grandeur
            ligne.value = ligne.value * facteur
            if ligne.sensor_id:
                ligne.source = "SENSOR"
            else:
                ligne.source = "DERIVED" if provenance == "SENSOR" else provenance
            ligne.save(update_fields=["quantity", "value", "source"])


def revenir(apps, schema_editor):
    """Vide `quantity` et remet les valeurs dans leur unite d'origine.

    Les lignes supprimees par la resolution de collisions ne reviennent pas :
    elles etaient redondantes par construction (la meme puissance ecrite deux
    fois dans deux unites), et rien ne serait perdu a ne pas les recreer.
    """
    Measurement = apps.get_model("measurements", "Measurement")
    for ancien, (_grandeur, facteur, _provenance, _prio) in CORRESPONDANCE.items():
        if facteur == 1.0:
            Measurement.objects.filter(measurement_type=ancien).update(quantity="")
            continue
        for ligne in Measurement.objects.filter(
            measurement_type=ancien
        ).iterator(chunk_size=2000):
            ligne.quantity = ""
            ligne.value = ligne.value / facteur
            ligne.save(update_fields=["quantity", "value"])


class Migration(migrations.Migration):

    dependencies = [
        ("measurements", "0009_grandeur_typee_et_provenance"),
    ]

    operations = [
        migrations.RunPython(migrer, revenir),
    ]

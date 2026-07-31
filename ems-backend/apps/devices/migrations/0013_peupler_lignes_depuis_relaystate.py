"""Peuple `Line`, `LineState` et `IoTNode` depuis les `RelayState` existants.

Le défaut corrigé : la ligne électrique n'existait pas comme entité. Elle était
trois colonnes booléennes (`line1`, `line2`, `line3`) sur un `RelayState` en
`OneToOne` avec la maison. Rien de ce qui la concerne ne pouvait donc être
nommé, historisé ni relié — on ne pouvait pas écrire « la ligne 2 a consommé
340 Wh hier », faute de sujet à qui rattacher la mesure.

Cette migration ne perd rien : `RelayState` reste en place jusqu'à l'étape 2.7,
et le sens inverse reconstruit les booléens depuis les `LineState`.
"""
from django.db import migrations


# Broches du prototype (esp32-firmware/.../config.h). Le firmware n'est PAS
# modifié par cette refonte : ces valeurs le décrivent, elles ne le pilotent
# pas. Un câblage différent se corrige en base, ligne par ligne.
GPIO_PAR_LIGNE = {1: 25, 2: 26, 3: 27}

# Noms par défaut. Volontairement neutres : les charges réellement rattachées
# sont portées par `Equipment`, et l'utilisateur peut renommer ses lignes.
NOM_PAR_LIGNE = {1: "Ligne 1", 2: "Ligne 2", 3: "Ligne 3"}


def peupler(apps, schema_editor):
    RelayState = apps.get_model("devices", "RelayState")
    Line = apps.get_model("devices", "Line")
    LineState = apps.get_model("devices", "LineState")
    IoTNode = apps.get_model("devices", "IoTNode")

    for state in RelayState.objects.all():
        etats = {
            1: state.line1,
            2: state.line2,
            3: state.line3,
        }
        for numero, ferme in etats.items():
            ligne, _ = Line.objects.get_or_create(
                house_id=state.house_id,
                number=numero,
                defaults={
                    "name": NOM_PAR_LIGNE[numero],
                    "relay_gpio": GPIO_PAR_LIGNE[numero],
                    "is_switchable": True,
                },
            )
            LineState.objects.get_or_create(
                line=ligne,
                defaults={
                    "is_closed": ferme,
                    # L'état voulu part de l'état constaté : au moment de la
                    # migration, aucune décision n'est en attente.
                    "desired_closed": ferme,
                    "last_commanded_at": state.last_commanded_at,
                    "updated_by_id": state.updated_by_id,
                },
            )

        # Le mode de pilotage et le jeton appartenaient au RelayState, donc à la
        # MAISON. Ils appartiennent en réalité au NŒUD : c'est lui qu'on
        # authentifie et lui qui pilote. Un second nœud pourra avoir son propre
        # jeton sans qu'on ait à révoquer celui du premier.
        IoTNode.objects.get_or_create(
            device_token=state.device_token,
            defaults={
                "house_id": state.house_id,
                "name": "ESP32 principal",
                "node_type": "ESP32_MAIN",
                "control_mode": state.control_mode,
                "last_contact_at": state.last_contact_at,
                "last_measurement_at": state.last_measurement_at,
                "last_report": state.last_report,
            },
        )


def depeupler(apps, schema_editor):
    """Recopie les états de ligne dans `RelayState` avant de vider les tables.

    Sans cette recopie, revenir en arrière après avoir piloté des lignes
    perdrait leur état : `RelayState` resterait figé sur ce qu'il valait au
    moment de la migration.
    """
    RelayState = apps.get_model("devices", "RelayState")
    Line = apps.get_model("devices", "Line")
    LineState = apps.get_model("devices", "LineState")
    IoTNode = apps.get_model("devices", "IoTNode")

    for state in RelayState.objects.all():
        for ligne in Line.objects.filter(house_id=state.house_id):
            etat = LineState.objects.filter(line=ligne).first()
            if etat is None or ligne.number not in (1, 2, 3):
                continue
            setattr(state, f"line{ligne.number}", etat.is_closed)
        state.save(update_fields=["line1", "line2", "line3"])

    LineState.objects.all().delete()
    Line.objects.all().delete()
    IoTNode.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0012_lignes_etats_et_noeuds"),
    ]

    operations = [
        migrations.RunPython(peupler, depeupler),
    ]

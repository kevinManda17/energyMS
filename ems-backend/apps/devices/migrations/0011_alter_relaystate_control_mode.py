"""Unification du vocabulaire : RelayState.control_mode « AUTO » -> « AUTOMATIC ».

Le backend, le web et le mobile écrivaient « AUTO » là où le moteur expert
produit `execution_mode = "AUTOMATIC"`. Deux chaînes pour la même idée : il
fallait traduire mentalement à chaque lecture, et une comparaison distraite les
confondait sans erreur visible.

La migration de données est indispensable : sans elle, tout micro-réseau déjà
passé en mode automatique retomberait silencieusement en mode manuel, puisque
« AUTO » ne correspondrait plus à aucun choix. Le sens inverse est fourni pour
que la migration reste réversible.
"""
from django.db import migrations, models


def auto_to_automatic(apps, schema_editor):
    RelayState = apps.get_model("devices", "RelayState")
    RelayState.objects.filter(control_mode="AUTO").update(control_mode="AUTOMATIC")


def automatic_to_auto(apps, schema_editor):
    RelayState = apps.get_model("devices", "RelayState")
    RelayState.objects.filter(control_mode="AUTOMATIC").update(control_mode="AUTO")


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0010_alter_sensor_options_equipment_load_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relaystate',
            name='control_mode',
            field=models.CharField(
                choices=[
                    ('MANUAL', 'Manuel'),
                    ('ASSISTED', "Assisté (l'expert propose)"),
                    ('AUTOMATIC', 'Automatique (expert)'),
                ],
                default='MANUAL',
                max_length=10,
            ),
        ),
        migrations.RunPython(auto_to_automatic, automatic_to_auto),
    ]

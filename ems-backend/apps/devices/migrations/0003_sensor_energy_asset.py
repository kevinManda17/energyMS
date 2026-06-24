import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_assets", "0001_initial"),
        ("devices", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sensor",
            name="energy_asset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sensors",
                to="energy_assets.energyasset",
            ),
        ),
        migrations.AlterField(
            model_name="sensor",
            name="sensor_type",
            field=models.CharField(
                choices=[
                    ("production", "Production"),
                    ("consumption", "Consumption"),
                    ("battery", "Battery"),
                    ("voltage", "Voltage"),
                    ("current", "Current"),
                    ("power", "Power"),
                    ("temperature", "Temperature"),
                    ("luminosity", "Luminosity"),
                    ("irradiance", "Irradiance"),
                ],
                max_length=20,
            ),
        ),
    ]


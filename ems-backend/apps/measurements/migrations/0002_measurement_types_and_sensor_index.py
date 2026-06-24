from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measurements", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="measurement",
            name="measurement_type",
            field=models.CharField(
                choices=[
                    ("production", "Production"),
                    ("consumption", "Consumption"),
                    ("battery_soc", "Battery SoC"),
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
        migrations.AddIndex(
            model_name="measurement",
            index=models.Index(
                fields=["sensor", "-timestamp"],
                name="measurement_sensor__8ce9f6_idx",
            ),
        ),
    ]


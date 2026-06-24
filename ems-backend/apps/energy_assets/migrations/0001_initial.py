# Generated for the EMS target architecture.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("houses", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnergyAsset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=120)),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("PV_PANEL", "Panneau photovoltaique"),
                            ("BATTERY", "Batterie"),
                            ("INVERTER", "Onduleur"),
                            ("SOLAR_CONTROLLER", "Regulateur solaire"),
                            ("GRID_SOURCE", "Source reseau"),
                            ("GENERATOR", "Generateur"),
                        ],
                        max_length=30,
                    ),
                ),
                ("nominal_power_kw", models.FloatField(blank=True, null=True)),
                ("capacity_kwh", models.FloatField(blank=True, null=True)),
                ("voltage", models.FloatField(blank=True, null=True)),
                ("current", models.FloatField(blank=True, null=True)),
                ("efficiency", models.FloatField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Actif"),
                            ("INACTIVE", "Inactif"),
                            ("FAULT", "Defaillant"),
                            ("MAINTENANCE", "Maintenance"),
                        ],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "house",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="energy_assets",
                        to="houses.house",
                    ),
                ),
            ],
            options={
                "ordering": ["house", "asset_type", "name"],
                "indexes": [
                    models.Index(
                        fields=["house", "asset_type"],
                        name="energy_asse_house_i_7bcaec_idx",
                    ),
                    models.Index(fields=["status"], name="energy_asse_status_30fcb4_idx"),
                ],
            },
        ),
    ]


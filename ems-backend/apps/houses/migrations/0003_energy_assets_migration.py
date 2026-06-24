from django.db import migrations


def move_capacity_fields_to_energy_assets(apps, schema_editor):
    House = apps.get_model("houses", "House")
    EnergyAsset = apps.get_model("energy_assets", "EnergyAsset")

    for house in House.objects.all():
        pv_capacity = getattr(house, "pv_capacity_kw", 0) or 0
        battery_capacity = getattr(house, "battery_capacity_kwh", 0) or 0

        if pv_capacity:
            EnergyAsset.objects.get_or_create(
                house_id=house.id,
                asset_type="PV_PANEL",
                name="Panneaux photovoltaiques",
                defaults={
                    "nominal_power_kw": pv_capacity,
                    "status": "ACTIVE",
                    "metadata": {"source": "migration_house_pv_capacity_kw"},
                },
            )

        if battery_capacity:
            EnergyAsset.objects.get_or_create(
                house_id=house.id,
                asset_type="BATTERY",
                name="Batterie principale",
                defaults={
                    "capacity_kwh": battery_capacity,
                    "status": "ACTIVE",
                    "metadata": {"source": "migration_house_battery_capacity_kwh"},
                },
            )


def noop_reverse(apps, schema_editor):
    # The old House capacity columns are intentionally removed after migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("energy_assets", "0001_initial"),
        ("houses", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(
            move_capacity_fields_to_energy_assets,
            reverse_code=noop_reverse,
        ),
        migrations.RemoveField(
            model_name="house",
            name="pv_capacity_kw",
        ),
        migrations.RemoveField(
            model_name="house",
            name="battery_capacity_kwh",
        ),
    ]


"""`EnergyAsset` passe en watts et wattheures (§2.7).

LE DEFAUT : `nominal_power_kw` et `capacity_kwh` portaient bien leur unite dans
le nom, mais laissaient CHAQUE LECTEUR reconvertir. `soc_service` multipliait
par 1000, `fuzzy_engine/engine.py` aussi, `forecasting/services.py` melangeait
les deux selon la fonction. Une meme capacite valait donc plusieurs choses
selon qui la lisait — et chaque nouveau lecteur etait une occasion de plus de
se tromper d'un facteur mille.

Le stockage passe en W et Wh (regle du §7 : W pour les puissances, Wh pour les
energies, conversion a l'affichage uniquement). Les valeurs sont multipliees
par 1000 ; le sens inverse divise, la migration est donc reversible sans perte.
"""
from django.db import migrations, models


FACTEUR = 1000.0


def vers_watts(apps, schema_editor):
    EnergyAsset = apps.get_model("energy_assets", "EnergyAsset")
    for actif in EnergyAsset.objects.all().iterator(chunk_size=1000):
        change = False
        if actif.nominal_power_w is not None:
            actif.nominal_power_w *= FACTEUR
            change = True
        if actif.capacity_wh is not None:
            actif.capacity_wh *= FACTEUR
            change = True
        if change:
            actif.save(update_fields=["nominal_power_w", "capacity_wh"])


def vers_kilowatts(apps, schema_editor):
    EnergyAsset = apps.get_model("energy_assets", "EnergyAsset")
    for actif in EnergyAsset.objects.all().iterator(chunk_size=1000):
        change = False
        if actif.nominal_power_w is not None:
            actif.nominal_power_w /= FACTEUR
            change = True
        if actif.capacity_wh is not None:
            actif.capacity_wh /= FACTEUR
            change = True
        if change:
            actif.save(update_fields=["nominal_power_w", "capacity_wh"])


class Migration(migrations.Migration):

    dependencies = [
        ("energy_assets", "0002_batterystate"),
    ]

    operations = [
        # Renommer AVANT de convertir : la conversion travaille sur le nouveau
        # nom, et l'ancien ne subsiste nulle part a mi-chemin.
        migrations.RenameField(
            model_name="energyasset",
            old_name="nominal_power_kw",
            new_name="nominal_power_w",
        ),
        migrations.RenameField(
            model_name="energyasset",
            old_name="capacity_kwh",
            new_name="capacity_wh",
        ),
        migrations.RunPython(vers_watts, vers_kilowatts),
    ]

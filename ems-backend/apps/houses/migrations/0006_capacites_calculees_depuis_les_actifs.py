"""`House.pv_capacity_kw` et `battery_capacity_kwh` sont retires (§2.7).

LE DEFAUT : deux sources pour la meme capacite, et elles DIVERGEAIENT.
`forecasting/services.py` retombait sur `House.pv_capacity_kw` quand aucun
panneau n'etait renseigne ; `fuzzy_engine/engine.py::_pv_nominal_power_kw`
l'ignorait purement et simplement. Le module de prevision et le moteur expert
raisonnaient donc sur des capacites differentes pour la meme maison, sans que
rien ne le signale.

Les proprietes calculees `House.pv_nominal_power_w` et
`House.battery_capacity_wh` les remplacent : une seule source, les actifs
eux-memes.

REPORT AVANT SUPPRESSION. Une capacite saisie sur la maison sans qu'aucun
panneau n'existe serait perdue par la simple suppression des colonnes. Elle est
donc convertie en `EnergyAsset` — ce qu'elle aurait du etre depuis le debut.
Le sens inverse recopie la somme des actifs vers la maison.
"""
from django.db import migrations


FACTEUR = 1000.0


def reporter_vers_les_actifs(apps, schema_editor):
    House = apps.get_model("houses", "House")
    EnergyAsset = apps.get_model("energy_assets", "EnergyAsset")

    for maison in House.objects.all().iterator(chunk_size=500):
        capacite_pv = getattr(maison, "pv_capacity_kw", None)
        if capacite_pv and not EnergyAsset.objects.filter(
            house=maison, asset_type="PV_PANEL"
        ).exists():
            EnergyAsset.objects.create(
                house=maison,
                name="Installation photovoltaique (estimation reportee)",
                asset_type="PV_PANEL",
                nominal_power_w=float(capacite_pv) * FACTEUR,
                status="ACTIVE",
                metadata={"origine": "House.pv_capacity_kw, reporte le 31/07/2026"},
            )

        capacite_batterie = getattr(maison, "battery_capacity_kwh", None)
        if capacite_batterie and not EnergyAsset.objects.filter(
            house=maison, asset_type="BATTERY"
        ).exists():
            EnergyAsset.objects.create(
                house=maison,
                name="Parc de batteries (estimation reportee)",
                asset_type="BATTERY",
                capacity_wh=float(capacite_batterie) * FACTEUR,
                status="ACTIVE",
                metadata={"origine": "House.battery_capacity_kwh, reporte le 31/07/2026"},
            )


def reporter_vers_la_maison(apps, schema_editor):
    """Sens inverse : recopie la somme des actifs vers les colonnes restaurees."""
    House = apps.get_model("houses", "House")
    EnergyAsset = apps.get_model("energy_assets", "EnergyAsset")

    for maison in House.objects.all().iterator(chunk_size=500):
        panneaux = EnergyAsset.objects.filter(
            house=maison, asset_type="PV_PANEL", status="ACTIVE"
        ).exclude(nominal_power_w__isnull=True)
        batteries = EnergyAsset.objects.filter(
            house=maison, asset_type="BATTERY", status="ACTIVE"
        ).exclude(capacity_wh__isnull=True)

        total_pv = sum(float(a.nominal_power_w or 0) for a in panneaux)
        total_batterie = sum(float(a.capacity_wh or 0) for a in batteries)
        maison.pv_capacity_kw = (total_pv / FACTEUR) or None
        maison.battery_capacity_kwh = (total_batterie / FACTEUR) or None
        maison.save(update_fields=["pv_capacity_kw", "battery_capacity_kwh"])


class Migration(migrations.Migration):

    dependencies = [
        ("houses", "0005_house_last_activity_at"),
        ("energy_assets", "0003_unites_en_watts"),
    ]

    operations = [
        migrations.RunPython(reporter_vers_les_actifs, reporter_vers_la_maison),
        migrations.RemoveField(model_name="house", name="pv_capacity_kw"),
        migrations.RemoveField(model_name="house", name="battery_capacity_kwh"),
    ]

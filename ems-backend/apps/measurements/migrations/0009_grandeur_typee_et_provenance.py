"""Grandeur TYPEE et provenance DECLAREE sur `Measurement` (§2.4).

Les CONTRAINTES ne sont pas posees ici mais dans la migration 0011, apres le
remplissage : une `CheckConstraint` exigeant un capteur pour toute mesure
`source=SENSOR` casserait sur les lignes existantes, dont l'origine n'est pas
encore declaree.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0013_peupler_lignes_depuis_relaystate'),
        ('houses', '0005_house_last_activity_at'),
        ('measurements', '0008_releve_par_ligne'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='quantity',
            field=models.CharField(blank=True, choices=[('pv_power_w', 'Puissance PV (W)'), ('load_power_w', 'Puissance appelée (W)'), ('grid_voltage_v', 'Tension réseau (V)'), ('grid_current_a', 'Courant total (A)'), ('battery_voltage_v', 'Tension batterie (V)'), ('battery_current_a', 'Courant batterie signé (A)'), ('battery_power_w', 'Puissance batterie (W)'), ('battery_temp_c', 'Température batterie (°C)'), ('battery_soc_pct', 'État de charge (%)'), ('pv_voltage_v', 'Tension PV (V)'), ('pv_current_a', 'Courant PV (A)'), ('module_temp_c', 'Température module (°C)'), ('ambient_temp_c', 'Température ambiante (°C)'), ('irradiance_wm2', 'Irradiance globale (W/m²)'), ('irradiance_tilt15_wm2', 'Irradiance inclinée 15° (W/m²)'), ('irradiance_tilt20_wm2', 'Irradiance inclinée 20° (W/m²)'), ('irradiance_east_wm2', 'Irradiance orientée est (W/m²)'), ('irradiance_west_wm2', 'Irradiance orientée ouest (W/m²)'), ('diffuse_wm2', 'Rayonnement diffus (W/m²)'), ('dni_wm2', 'Irradiance directe normale (W/m²)'), ('humidity_pct', 'Humidité relative (%)'), ('wind_speed_ms', 'Vitesse du vent (m/s)'), ('wind_direction_deg', 'Direction du vent (°)'), ('air_pressure_hpa', 'Pression atmosphérique (hPa)')], db_index=True, max_length=28),
        ),
        migrations.AddField(
            model_name='measurement',
            name='source',
            field=models.CharField(choices=[('SENSOR', 'Mesurée par un capteur'), ('WEATHER_API', "Estimée par l'API météo"), ('DERIVED', "Calculée à partir d'autres mesures"), ('MANUAL', 'Saisie manuellement')], default='DERIVED', max_length=12),
        ),
        migrations.AddIndex(
            model_name='measurement',
            index=models.Index(fields=['house', 'quantity', '-timestamp'], name='measurement_house_i_629590_idx'),
        ),
    ]

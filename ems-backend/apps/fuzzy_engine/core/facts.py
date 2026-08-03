from __future__ import annotations

from .membership import (
    balance_at_most_deficit,
    clamp,
    fuzzify_battery_soc,
    fuzzify_battery_temperature,
    fuzzify_current_load_ratio,
    fuzzify_data_quality,
    fuzzify_energy_balance_ratio,
    fuzzify_irradiance,
    fuzzify_pv_generation_ratio,
    module_derating,
    presence_level,
    probe_implausibility,
    pv_at_most_low,
    soc_at_least_medium,
    soc_at_most_low,
    temperature_at_least_high,
)
from .models import EnergyFacts


def fuzzify_facts(facts: EnergyFacts) -> dict:
    energy_balance_ratio = facts.forecast_pv_energy_kwh / max(facts.forecast_load_energy_kwh, 0.001)
    current_load_ratio = facts.current_load_power_kw / max(facts.current_pv_power_kw, 0.001)
    pv_generation_ratio = facts.current_pv_power_kw / max(facts.pv_nominal_power_kw, 0.001)

    return {
        "derived": {
            "energy_balance_ratio": energy_balance_ratio,
            "current_load_ratio": current_load_ratio,
            "pv_generation_ratio": pv_generation_ratio,
        },
        "battery_soc": fuzzify_battery_soc(facts.battery_soc_percent),
        "battery_temperature": fuzzify_battery_temperature(facts.battery_temperature_c),
        "energy_balance": fuzzify_energy_balance_ratio(energy_balance_ratio),
        "current_load": fuzzify_current_load_ratio(current_load_ratio),
        "pv_generation": fuzzify_pv_generation_ratio(pv_generation_ratio),
        "data_quality": fuzzify_data_quality(
            facts.data_quality, facts.data_completeness
        ),
        # Contexte : météo, sonde module, horloge, régime de pilotage. Chacun
        # de ces faits était transmis au moteur et tracé dans la Decision sans
        # qu'AUCUNE règle ne le lise — six promesses non tenues. Chacun vaut 0
        # quand sa source manque, jamais une valeur par défaut plausible.
        "irradiance": (
            fuzzify_irradiance(facts.solar_irradiance_wm2)
            if facts.solar_irradiance_wm2 is not None
            else {"dark": 0.0, "weak": 0.0, "strong": 0.0}
        ),
        "irradiance_known": 1.0 if facts.solar_irradiance_wm2 is not None else 0.0,
        "context": {
            # Perte de rendement attendue des modules du fait de leur chaleur.
            "module_derating": (
                module_derating(facts.module_temperature_c)
                if facts.module_temperature_c is not None
                else 0.0
            ),
            # Présence attendue au domicile (heure + jour de la semaine).
            "presence": presence_level(facts.hour, facts.day_of_week),
            # Cohérence entre la sonde batterie et la température ambiante.
            "probe_implausibility": probe_implausibility(
                facts.battery_temperature_c, facts.ambient_temperature_c
            ),
            # Chaleur ambiante : une batterie dans un local chaud dérive.
            "hot_ambient": (
                clamp((facts.ambient_temperature_c - 30.0) / 10.0, 0.0, 1.0)
                if facts.ambient_temperature_c is not None
                else 0.0
            ),
        },
        # Régime de pilotage : crisp, mais exposé comme les autres pour que les
        # règles s'écrivent toutes de la même façon.
        "operating_mode": {
            "manual": 1.0 if facts.operating_mode == "MANUAL" else 0.0,
            "assisted": 1.0 if facts.operating_mode == "ASSISTED" else 0.0,
            # "AUTO" reste accepté : c'est l'ancien libellé, et une décision
            # archivée ou un client non encore déployé peut encore l'envoyer.
            "automatic": 1.0 if facts.operating_mode in ("AUTO", "AUTOMATIC") else 0.0,
        },
        # Lectures cumulatives « ce terme ou pire ». Fuzzifiées ici, donc
        # tracées dans la Decision au même titre que les ensembles : une règle
        # qui s'en sert reste vérifiable a posteriori.
        "cumulative": {
            "soc_at_most_low": soc_at_most_low(facts.battery_soc_percent),
            # Prémisse de RELÂCHEMENT, en remplacement de l'autonomie.
            "soc_at_least_medium": soc_at_least_medium(facts.battery_soc_percent),
            "pv_at_most_low": pv_at_most_low(pv_generation_ratio),
            "balance_at_most_deficit": balance_at_most_deficit(energy_balance_ratio),
            "temperature_at_least_high": temperature_at_least_high(
                facts.battery_temperature_c
            ),
        },
    }

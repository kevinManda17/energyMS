from __future__ import annotations

from .membership import (
    autonomy_at_least_comfortable,
    autonomy_at_most_short,
    balance_at_most_deficit,
    fuzzify_autonomy_hours,
    fuzzify_battery_soc,
    fuzzify_battery_temperature,
    fuzzify_current_load_ratio,
    fuzzify_data_quality,
    fuzzify_energy_balance_ratio,
    fuzzify_pv_generation_ratio,
    pv_at_most_low,
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
        "data_quality": fuzzify_data_quality(facts.data_quality),
        # Autonomie : tous les termes à zéro quand elle n'est pas calculable
        # (SOC ou capacité inconnus). Une règle d'autonomie ne se déclenche
        # alors pas — elle ne se déclenche pas « en faveur du calme » non plus,
        # elle ne se déclenche simplement pas. `known` permet aux règles de
        # distinguer « autonomie confortable » de « autonomie inconnue ».
        "autonomy": (
            fuzzify_autonomy_hours(facts.autonomy_hours)
            if facts.autonomy_hours is not None
            else {"critical": 0.0, "short": 0.0, "comfortable": 0.0, "large": 0.0}
        ),
        "autonomy_known": 1.0 if facts.autonomy_hours is not None else 0.0,
        # Lectures cumulatives « ce terme ou pire ». Fuzzifiées ici, donc
        # tracées dans la Decision au même titre que les ensembles : une règle
        # qui s'en sert reste vérifiable a posteriori.
        "cumulative": {
            "soc_at_most_low": soc_at_most_low(facts.battery_soc_percent),
            "pv_at_most_low": pv_at_most_low(pv_generation_ratio),
            "balance_at_most_deficit": balance_at_most_deficit(energy_balance_ratio),
            "temperature_at_least_high": temperature_at_least_high(
                facts.battery_temperature_c
            ),
            "autonomy_at_most_short": (
                autonomy_at_most_short(facts.autonomy_hours)
                if facts.autonomy_hours is not None
                else 0.0
            ),
            # Prémisse de RELÂCHEMENT. Vaut 0 quand l'autonomie est inconnue :
            # le moteur ne se rassure jamais sur une donnée qu'il n'a pas.
            "autonomy_at_least_comfortable": (
                autonomy_at_least_comfortable(facts.autonomy_hours)
                if facts.autonomy_hours is not None
                else 0.0
            ),
        },
    }

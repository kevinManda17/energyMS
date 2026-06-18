from __future__ import annotations

from .membership import (
    fuzzify_battery_soc,
    fuzzify_battery_temperature,
    fuzzify_current_load_ratio,
    fuzzify_data_quality,
    fuzzify_energy_balance_ratio,
    fuzzify_pv_generation_ratio,
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
    }

from __future__ import annotations


def clamp(value: float, min_value: float, max_value: float) -> float:
    if min_value > max_value:
        raise ValueError("min_value must be <= max_value")
    return max(min_value, min(max_value, float(value)))


def triangular(x: float, a: float, b: float, c: float) -> float:
    x = float(x)
    if a > b or b > c:
        raise ValueError("triangular requires a <= b <= c")
    if a == b == c:
        return 1.0 if x == a else 0.0
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return clamp((x - a) / max(b - a, 1e-12), 0.0, 1.0)
    return clamp((c - x) / max(c - b, 1e-12), 0.0, 1.0)


def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
    x = float(x)
    if a > b or b > c or c > d:
        raise ValueError("trapezoidal requires a <= b <= c <= d")
    if a == b and x <= b:
        return 1.0
    if c == d and x >= c:
        return 1.0
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return clamp((x - a) / max(b - a, 1e-12), 0.0, 1.0)
    return clamp((d - x) / max(d - c, 1e-12), 0.0, 1.0)


def fuzzify_battery_soc(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 100.0)
    return {
        "critical": trapezoidal(x, 0, 0, 15, 25),
        "low": triangular(x, 15, 30, 45),
        "medium": triangular(x, 35, 55, 75),
        "high": trapezoidal(x, 65, 85, 100, 100),
    }


def fuzzify_battery_temperature(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 80.0)
    return {
        "normal": trapezoidal(x, 0, 0, 30, 40),
        "high": triangular(x, 35, 45, 55),
        "dangerous": trapezoidal(x, 50, 60, 80, 80),
    }


def fuzzify_energy_balance_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 2.0)
    return {
        "critical_deficit": trapezoidal(x, 0, 0, 0.35, 0.60),
        "deficit": triangular(x, 0.45, 0.70, 0.95),
        "balanced": triangular(x, 0.85, 1.0, 1.20),
        "surplus": trapezoidal(x, 1.10, 1.35, 2.0, 2.0),
    }


def fuzzify_current_load_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 3.0)
    return {
        "low": trapezoidal(x, 0, 0, 0.5, 0.9),
        "medium": triangular(x, 0.7, 1.1, 1.5),
        "high": trapezoidal(x, 1.3, 1.8, 3.0, 3.0),
    }


def fuzzify_pv_generation_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 1.0)
    return {
        "very_low": trapezoidal(x, 0, 0, 0.10, 0.25),
        "low": triangular(x, 0.15, 0.35, 0.55),
        "medium": triangular(x, 0.45, 0.65, 0.80),
        "high": trapezoidal(x, 0.70, 0.85, 1.0, 1.0),
    }


def fuzzify_data_quality(value: str) -> dict[str, float]:
    normalized = (value or "").strip().upper()
    return {
        "good": 1.0 if normalized == "GOOD" else 0.0,
        "partial": 0.5 if normalized == "PARTIAL" else 0.0,
        "bad": 1.0 if normalized == "BAD" else 0.0,
    }

from __future__ import annotations

from .models import GisConfig


def annual_gis(age: int, other_income: float, config: GisConfig) -> float:
    if not config.enabled or age < 65 or age >= 75:
        return 0.0
    if other_income >= config.income_cutoff:
        return 0.0
    return max(0.0, config.annual_max - (max(0.0, other_income) / 2))

from __future__ import annotations

from . import policy


def oas_start_factor(start_age: int) -> tuple[float, str | None]:
    effective_age = min(max(start_age, 65), 70)
    warning = None
    if start_age > 70:
        warning = (
            "OAS deferral increase is capped at age 70; "
            "payment still starts at configured age."
        )
    if start_age < 65:
        warning = "OAS cannot start before age 65; calculations use age 65 for the deferral factor."
    return 1 + ((effective_age - 65) * 12 * 0.006), warning


def annual_oas(
    age: int,
    start_age: int,
    annual_amount_65_to_74: float,
    growth: float,
) -> tuple[float, str | None]:
    if age < start_age or age < 65:
        return 0.0, None

    factor, warning = oas_start_factor(start_age)
    effective_age = min(max(start_age, 65), 70)
    age_75_ratio = policy.OAS_MAX_MONTHLY_75_PLUS / policy.OAS_MAX_MONTHLY_65_TO_74
    base = annual_amount_65_to_74 * (age_75_ratio if age >= 75 else 1.0)
    grown = base * ((1 + growth) ** max(0, age - effective_age))
    return grown * factor, warning


def oas_recovery(age: int, net_world_income: float, oas_amount: float) -> float:
    if oas_amount <= 0:
        return 0.0
    maximum_threshold = (
        policy.OAS_RECOVERY_MAX_75_PLUS if age >= 75 else policy.OAS_RECOVERY_MAX_65_TO_74
    )
    if net_world_income >= maximum_threshold:
        return oas_amount
    excess = max(0.0, net_world_income - policy.OAS_RECOVERY_THRESHOLD_2026)
    return min(oas_amount, excess * policy.OAS_RECOVERY_RATE)

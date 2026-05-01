from __future__ import annotations


def cpp_start_factor(start_age: int) -> tuple[float, str | None]:
    effective_age = min(start_age, 70)
    warning = None
    if start_age > 70:
        warning = (
            "CPP deferral increase is capped at age 70; "
            "payment still starts at configured age."
        )

    if effective_age < 65:
        factor = 1 - ((65 - effective_age) * 12 * 0.006)
    else:
        factor = 1 + ((effective_age - 65) * 12 * 0.007)
    return max(0.0, factor), warning


def annual_cpp(
    age: int,
    start_age: int,
    annual_amount_at_65: float,
    growth: float,
) -> tuple[float, str | None]:
    if age < start_age:
        return 0.0, None
    factor, warning = cpp_start_factor(start_age)
    effective_age = min(start_age, 70)
    grown = annual_amount_at_65 * ((1 + growth) ** max(0, age - effective_age))
    return grown * factor, warning

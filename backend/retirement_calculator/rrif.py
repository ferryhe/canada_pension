from __future__ import annotations

from . import policy


def minimum_withdrawal_factor(age: int) -> float:
    if age < 65:
        return 0.0
    if age < 71:
        return 1 / (90 - age)
    if age >= 95:
        return policy.RRIF_FACTORS_71_PLUS[95]
    return policy.RRIF_FACTORS_71_PLUS[age]

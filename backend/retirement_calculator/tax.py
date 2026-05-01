from __future__ import annotations

from . import policy
from .models import TaxBreakdown


def progressive_tax(income: float, brackets: list[policy.Bracket]) -> float:
    taxable = max(0.0, income)
    total = 0.0
    ordered = sorted(brackets, key=lambda bracket: bracket.threshold)
    for index, bracket in enumerate(ordered):
        next_threshold = ordered[index + 1].threshold if index + 1 < len(ordered) else None
        lower = bracket.threshold
        upper = next_threshold if next_threshold is not None else taxable
        if taxable <= lower:
            continue
        total += (min(taxable, upper) - lower) * bracket.rate
    return max(0.0, total)


def federal_basic_personal_amount(net_income: float) -> float:
    if net_income <= policy.FEDERAL_BPA_PHASEOUT_START:
        return policy.FEDERAL_BASIC_PERSONAL_MAX
    if net_income >= policy.FEDERAL_BPA_PHASEOUT_END:
        return policy.FEDERAL_BASIC_PERSONAL_MIN

    phaseout_range = policy.FEDERAL_BPA_PHASEOUT_END - policy.FEDERAL_BPA_PHASEOUT_START
    extra = policy.FEDERAL_BASIC_PERSONAL_MAX - policy.FEDERAL_BASIC_PERSONAL_MIN
    fraction = (net_income - policy.FEDERAL_BPA_PHASEOUT_START) / phaseout_range
    return policy.FEDERAL_BASIC_PERSONAL_MAX - extra * fraction


def federal_tax(income: float) -> float:
    gross_tax = progressive_tax(income, policy.FEDERAL_BRACKETS)
    credit = federal_basic_personal_amount(income) * policy.FEDERAL_BRACKETS[0].rate
    return max(0.0, gross_tax - credit)


def ontario_basic_tax(income: float) -> float:
    gross_tax = progressive_tax(income, policy.ONTARIO_BRACKETS)
    credit = policy.ONTARIO_BASIC_PERSONAL_AMOUNT * policy.ONTARIO_BRACKETS[0].rate
    return max(0.0, gross_tax - credit)


def ontario_tax_reduction(provincial_tax_before_reduction: float) -> float:
    maximum_reduction = policy.ONTARIO_TAX_REDUCTION_BASIC * 2
    if provincial_tax_before_reduction >= maximum_reduction:
        return 0.0
    return min(
        provincial_tax_before_reduction,
        maximum_reduction - provincial_tax_before_reduction,
    )


def ontario_surtax(provincial_tax_before_surtax: float) -> float:
    surtax = 0.0
    if provincial_tax_before_surtax > policy.ONTARIO_SURTAX_THRESHOLD_1:
        surtax += (provincial_tax_before_surtax - policy.ONTARIO_SURTAX_THRESHOLD_1) * 0.20
    if provincial_tax_before_surtax > policy.ONTARIO_SURTAX_THRESHOLD_2:
        surtax += (provincial_tax_before_surtax - policy.ONTARIO_SURTAX_THRESHOLD_2) * 0.36
    return max(0.0, surtax)


def ontario_health_premium(taxable_income: float) -> float:
    income = max(0.0, taxable_income)
    if income <= 20_000:
        return 0.0
    if income <= 36_000:
        return min(300.0, (income - 20_000) * 0.06)
    if income <= 48_000:
        return min(450.0, 300.0 + (income - 36_000) * 0.06)
    if income <= 72_000:
        return min(600.0, 450.0 + (income - 48_000) * 0.25)
    if income <= 200_000:
        return min(750.0, 600.0 + (income - 72_000) * 0.25)
    return min(900.0, 750.0 + (income - 200_000) * 0.25)


def calculate_income_tax(taxable_income: float, oas_recovery: float = 0.0) -> TaxBreakdown:
    federal = federal_tax(taxable_income)
    provincial_before_reduction = ontario_basic_tax(taxable_income)
    provincial_reduction = ontario_tax_reduction(provincial_before_reduction)
    provincial = max(0.0, provincial_before_reduction - provincial_reduction)
    surtax = ontario_surtax(provincial)
    health = ontario_health_premium(taxable_income)
    total = federal + provincial + surtax + health + max(0.0, oas_recovery)

    return TaxBreakdown(
        taxable_income=round(taxable_income, 2),
        federal_tax=round(federal, 2),
        ontario_tax=round(provincial, 2),
        ontario_surtax=round(surtax, 2),
        ontario_health_premium=round(health, 2),
        oas_recovery=round(oas_recovery, 2),
        total_tax=round(total, 2),
    )

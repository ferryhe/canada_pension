from __future__ import annotations

from . import cpp, gis, oas, policy, rrif, tax
from .models import (
    AccountSnapshot,
    BenefitBreakdown,
    SimulationConfig,
    SimulationResult,
    Summary,
    WithdrawalBreakdown,
    YearlyResult,
)


def _round_money(value: float) -> float:
    return round(max(0.0, value), 2)


def _net_worth(
    tfsa: float,
    rrsp: float,
    non_registered: float,
    investment_asset: float,
    investment_loan: float,
    spouse_rrsp: float,
) -> float:
    return tfsa + rrsp + non_registered + investment_asset + spouse_rrsp - investment_loan


def simulate(config: SimulationConfig | None = None) -> SimulationResult:
    cfg = config or SimulationConfig()
    warnings: list[str] = []
    results: list[YearlyResult] = []

    tfsa_balance = cfg.accounts.tfsa.balance
    rrsp_balance = cfg.accounts.rrsp.balance
    non_registered_balance = cfg.accounts.non_registered.balance
    investment_asset = cfg.accounts.investment_loan.gross_asset_balance
    investment_loan = cfg.accounts.investment_loan.loan_balance
    spouse_rrsp_balance = cfg.accounts.spouse_rrsp.balance

    annual_return = cfg.assumptions.annual_return
    growth = cfg.assumptions.oas_cpp_growth

    if cfg.benefits.oas.start_age > 70:
        warnings.append("OAS start age is above 70; deferral increase is capped at age 70.")
    if cfg.benefits.cpp.start_age > 70:
        warnings.append("CPP start age is above 70; deferral increase is capped at age 70.")
    if cfg.accounts.rrsp.annual_contribution > policy.RRSP_DOLLAR_LIMIT:
        warnings.append(
            "RRSP annual contribution exceeds the 2026 dollar limit of "
            f"${policy.RRSP_DOLLAR_LIMIT:,.0f}; "
            "the contribution is capped in the projection."
        )
    if cfg.accounts.tfsa.annual_contribution > policy.TFSA_DOLLAR_LIMIT:
        warnings.append(
            "TFSA annual contribution exceeds the 2026 dollar limit of "
            f"${policy.TFSA_DOLLAR_LIMIT:,.0f}; "
            "the contribution is capped in the projection."
        )
    spouse_rrsp_in_use = (
        cfg.accounts.spouse_rrsp.balance > 0 or cfg.accounts.spouse_rrsp.annual_contribution > 0
    )
    if spouse_rrsp_in_use:
        warnings.append(
            "Spouse RRSP is modeled as household cash flow only; spouse OAS, CPP, GIS, "
            "and a separate spouse tax return are not calculated in this MVP."
        )

    for age in range(cfg.profile.current_age, cfg.profile.projection_end_age + 1):
        year = policy.POLICY_YEAR + (age - cfg.profile.current_age)
        phase = "retirement" if age >= cfg.profile.retirement_age else "accumulation"
        year_warnings: list[str] = []

        tfsa_withdrawal = 0.0
        rrsp_withdrawal = 0.0
        non_registered_withdrawal = 0.0
        spouse_rrsp_withdrawal = 0.0
        investment_loan_repayment = 0.0

        tfsa_contribution = (
            min(cfg.accounts.tfsa.annual_contribution, policy.TFSA_DOLLAR_LIMIT)
            if phase == "accumulation"
            else 0.0
        )
        rrsp_contribution = (
            min(cfg.accounts.rrsp.annual_contribution, policy.RRSP_DOLLAR_LIMIT)
            if phase == "accumulation"
            else 0.0
        )
        non_registered_contribution = (
            cfg.accounts.non_registered.annual_contribution if phase == "accumulation" else 0.0
        )
        spouse_rrsp_contribution = (
            cfg.accounts.spouse_rrsp.annual_contribution if phase == "accumulation" else 0.0
        )

        if phase == "retirement":
            tfsa_withdrawal = min(tfsa_balance, tfsa_balance * cfg.withdrawal_strategy.tfsa_rate)
            non_registered_withdrawal = min(
                non_registered_balance,
                non_registered_balance * cfg.withdrawal_strategy.non_registered_rate,
            )
            if age >= 71:
                rrsp_withdrawal = min(
                    rrsp_balance,
                    rrsp_balance * rrif.minimum_withdrawal_factor(age),
                )
            spouse_rrsp_withdrawal = min(
                spouse_rrsp_balance,
                spouse_rrsp_balance * cfg.withdrawal_strategy.spouse_rrsp_rate,
            )
            investment_loan_repayment = min(
                investment_loan,
                cfg.accounts.investment_loan.annual_repayment,
            )

        cpp_amount, cpp_warning = cpp.annual_cpp(
            age,
            cfg.benefits.cpp.start_age,
            cfg.benefits.cpp.annual_amount,
            growth,
        )
        oas_amount, oas_warning = oas.annual_oas(
            age,
            cfg.benefits.oas.start_age,
            cfg.benefits.oas.annual_amount,
            growth,
        )
        for warning in (cpp_warning, oas_warning):
            if warning and warning not in year_warnings:
                year_warnings.append(warning)

        taxable_capital_gain = (
            non_registered_withdrawal
            * cfg.withdrawal_strategy.capital_gain_ratio
            * cfg.tax.capital_gains_inclusion_rate
        )
        loan_interest_deduction = investment_loan * cfg.accounts.investment_loan.interest_rate
        taxable_before_gis = max(
            0.0,
            rrsp_withdrawal
            + spouse_rrsp_withdrawal
            + taxable_capital_gain
            + cpp_amount
            + oas_amount
            - loan_interest_deduction,
        )
        other_income_for_gis = max(
            0.0,
            rrsp_withdrawal
            + spouse_rrsp_withdrawal
            + taxable_capital_gain
            + cpp_amount
            - loan_interest_deduction,
        )
        gis_amount = gis.annual_gis(age, other_income_for_gis, cfg.benefits.gis)
        oas_recovery_amount = oas.oas_recovery(age, taxable_before_gis, oas_amount)
        tax_breakdown = tax.calculate_income_tax(taxable_before_gis, oas_recovery_amount)

        gross_cash = (
            tfsa_withdrawal
            + rrsp_withdrawal
            + non_registered_withdrawal
            + spouse_rrsp_withdrawal
            + cpp_amount
            + oas_amount
            + gis_amount
            - investment_loan_repayment
            - loan_interest_deduction
        )
        after_tax_income = gross_cash - tax_breakdown.total_tax

        tfsa_balance = max(
            0.0,
            tfsa_balance * (1 + annual_return) + tfsa_contribution - tfsa_withdrawal,
        )
        rrsp_balance = max(
            0.0,
            rrsp_balance * (1 + annual_return) + rrsp_contribution - rrsp_withdrawal,
        )
        non_registered_balance = max(
            0.0,
            non_registered_balance * (1 + annual_return)
            + non_registered_contribution
            - non_registered_withdrawal,
        )
        investment_asset = max(0.0, investment_asset * (1 + annual_return))
        investment_loan = max(0.0, investment_loan - investment_loan_repayment)
        spouse_rrsp_balance = max(
            0.0,
            spouse_rrsp_balance * (1 + annual_return)
            + spouse_rrsp_contribution
            - spouse_rrsp_withdrawal,
        )

        accounts = AccountSnapshot(
            tfsa=_round_money(tfsa_balance),
            rrsp=_round_money(rrsp_balance),
            non_registered=_round_money(non_registered_balance),
            investment_asset=_round_money(investment_asset),
            investment_loan=_round_money(investment_loan),
            spouse_rrsp=_round_money(spouse_rrsp_balance),
            net_worth=round(
                _net_worth(
                    tfsa_balance,
                    rrsp_balance,
                    non_registered_balance,
                    investment_asset,
                    investment_loan,
                    spouse_rrsp_balance,
                ),
                2,
            ),
        )

        results.append(
            YearlyResult(
                year=year,
                age=age,
                phase=phase,
                withdrawals=WithdrawalBreakdown(
                    tfsa=_round_money(tfsa_withdrawal),
                    rrsp=_round_money(rrsp_withdrawal),
                    non_registered=_round_money(non_registered_withdrawal),
                    investment_loan_repayment=_round_money(investment_loan_repayment),
                    spouse_rrsp=_round_money(spouse_rrsp_withdrawal),
                ),
                benefits=BenefitBreakdown(
                    oas=_round_money(oas_amount),
                    oas_recovery=_round_money(oas_recovery_amount),
                    cpp=_round_money(cpp_amount),
                    gis=_round_money(gis_amount),
                ),
                tax=tax_breakdown,
                after_tax_income=round(after_tax_income, 2),
                accounts=accounts,
                warnings=year_warnings,
            )
        )

    summary_results = [result for result in results if result.age <= cfg.profile.life_expectancy]
    if not summary_results:
        summary_results = results
    retirement_results = [
        result for result in summary_results if result.age >= cfg.profile.retirement_age
    ]
    first_retirement = retirement_results[0] if retirement_results else summary_results[-1]
    total_after_tax = sum(max(0.0, result.after_tax_income) for result in retirement_results)
    average_after_tax = total_after_tax / len(retirement_results) if retirement_results else 0.0
    ending_net_worth = summary_results[-1].accounts.net_worth
    lowest_net_worth = min(result.accounts.net_worth for result in summary_results)
    peak_taxable_income = max(result.tax.taxable_income for result in summary_results)

    suggestions = _build_suggestions(cfg, summary_results)

    return SimulationResult(
        yearly_results=results,
        summary=Summary(
            retirement_year=policy.POLICY_YEAR
            + (cfg.profile.retirement_age - cfg.profile.current_age),
            summary_end_age=summary_results[-1].age,
            first_retirement_after_tax_income=round(first_retirement.after_tax_income, 2),
            average_retirement_after_tax_income=round(average_after_tax, 2),
            total_after_tax_income=round(total_after_tax, 2),
            ending_net_worth=round(ending_net_worth, 2),
            lowest_net_worth=round(lowest_net_worth, 2),
            peak_taxable_income=round(peak_taxable_income, 2),
            suggestions=suggestions,
        ),
        warnings=warnings,
        source_version=policy.source_version(),
    )


def _build_suggestions(cfg: SimulationConfig, results: list[YearlyResult]) -> list[str]:
    suggestions: list[str] = []
    if cfg.benefits.oas.start_age > 70 or cfg.benefits.cpp.start_age > 70:
        suggestions.append(
            "OAS/CPP deferral increases stop at age 70; "
            "starting later delays cash flow without extra uplift."
        )
    if (
        cfg.accounts.rrsp.annual_contribution < policy.RRSP_DOLLAR_LIMIT
        and cfg.profile.current_age < cfg.profile.retirement_age
    ):
        suggestions.append(
            "RRSP contributions are below the 2026 dollar limit; "
            "compare higher contributions if current tax rate is high."
        )
    if any(result.benefits.oas_recovery > 0 for result in results):
        suggestions.append(
            "OAS recovery tax appears in the projection; "
            "use TFSA and non-registered withdrawals to smooth taxable income."
        )
    if any(result.benefits.gis > 0 for result in results):
        suggestions.append(
            "GIS is sensitive to taxable income; "
            "avoid unnecessary RRSP withdrawals before age 75 if GIS preservation matters."
        )
    if not suggestions:
        suggestions.append(
            "The baseline projection is stable; "
            "compare retirement age and benefit start age scenarios next."
        )
    return suggestions

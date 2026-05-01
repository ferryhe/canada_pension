from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import policy


class ProfileConfig(BaseModel):
    current_age: int = Field(40, ge=18, le=100)
    retirement_age: int = Field(65, ge=45, le=75)
    life_expectancy: int = Field(95, ge=60, le=110)
    projection_end_age: int = Field(100, ge=60, le=110)

    @model_validator(mode="after")
    def validate_ages(self) -> ProfileConfig:
        if self.retirement_age < self.current_age:
            raise ValueError("retirement_age must be greater than or equal to current_age")
        if self.projection_end_age < self.current_age:
            raise ValueError("projection_end_age must be greater than or equal to current_age")
        if self.life_expectancy < self.retirement_age:
            raise ValueError("life_expectancy must be greater than or equal to retirement_age")
        return self


class AccountConfig(BaseModel):
    balance: float = Field(0, ge=0)
    annual_contribution: float = Field(0, ge=0)


class InvestmentLoanConfig(BaseModel):
    balance: float = Field(300_000, ge=0)
    annual_repayment: float = Field(15_000, ge=0)
    interest_rate: float = Field(0.05, ge=0, le=1)


class AccountsConfig(BaseModel):
    tfsa: AccountConfig = Field(default_factory=lambda: AccountConfig(balance=50_000))
    rrsp: AccountConfig = Field(
        default_factory=lambda: AccountConfig(balance=500_000, annual_contribution=33_000)
    )
    non_registered: AccountConfig = Field(default_factory=lambda: AccountConfig(balance=50_000))
    investment_loan: InvestmentLoanConfig = Field(default_factory=InvestmentLoanConfig)
    spouse_rrsp: AccountConfig = Field(default_factory=lambda: AccountConfig(balance=300_000))


class AssumptionsConfig(BaseModel):
    annual_return: float = Field(0.08, ge=-0.5, le=0.5)
    inflation: float = Field(0.03, ge=0, le=0.2)
    oas_cpp_growth: float = Field(0.025, ge=0, le=0.2)


class BenefitStartConfig(BaseModel):
    start_age: int = Field(71, ge=60, le=75)
    annual_amount: float = Field(0, ge=0)


class GisConfig(BaseModel):
    enabled: bool = True
    annual_max: float = Field(policy.GIS_SINGLE_MAX_MONTHLY * 12, ge=0)
    income_cutoff: float = Field(policy.GIS_SINGLE_INCOME_CUTOFF, ge=0)


class BenefitsConfig(BaseModel):
    oas: BenefitStartConfig = Field(
        default_factory=lambda: BenefitStartConfig(
            start_age=71,
            annual_amount=policy.OAS_MAX_MONTHLY_65_TO_74 * 12,
        )
    )
    cpp: BenefitStartConfig = Field(
        default_factory=lambda: BenefitStartConfig(start_age=71, annual_amount=16_747)
    )
    gis: GisConfig = Field(default_factory=GisConfig)


class TaxConfig(BaseModel):
    province: Literal["ON"] = "ON"
    capital_gains_inclusion_rate: float = Field(policy.CAPITAL_GAINS_INCLUSION_RATE, ge=0, le=1)


class WithdrawalStrategyConfig(BaseModel):
    tfsa_rate: float = Field(0.05, ge=0, le=1)
    non_registered_rate: float = Field(0.05, ge=0, le=1)
    capital_gain_ratio: float = Field(0.5, ge=0, le=1)
    spouse_rrsp_rate: float = Field(0.04, ge=0, le=1)


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    accounts: AccountsConfig = Field(default_factory=AccountsConfig)
    assumptions: AssumptionsConfig = Field(default_factory=AssumptionsConfig)
    benefits: BenefitsConfig = Field(default_factory=BenefitsConfig)
    tax: TaxConfig = Field(default_factory=TaxConfig)
    withdrawal_strategy: WithdrawalStrategyConfig = Field(default_factory=WithdrawalStrategyConfig)

    @field_validator("tax")
    @classmethod
    def validate_tax(cls, tax: TaxConfig) -> TaxConfig:
        if tax.province != "ON":
            raise ValueError("MVP supports Ontario only")
        return tax


class BenefitBreakdown(BaseModel):
    oas: float = 0
    oas_recovery: float = 0
    cpp: float = 0
    gis: float = 0


class WithdrawalBreakdown(BaseModel):
    tfsa: float = 0
    rrsp: float = 0
    non_registered: float = 0
    investment_loan_repayment: float = 0
    spouse_rrsp: float = 0


class TaxBreakdown(BaseModel):
    taxable_income: float = 0
    federal_tax: float = 0
    ontario_tax: float = 0
    ontario_surtax: float = 0
    ontario_health_premium: float = 0
    oas_recovery: float = 0
    total_tax: float = 0


class AccountSnapshot(BaseModel):
    tfsa: float = 0
    rrsp: float = 0
    non_registered: float = 0
    investment_asset: float = 0
    investment_loan: float = 0
    spouse_rrsp: float = 0
    net_worth: float = 0


class YearlyResult(BaseModel):
    year: int
    age: int
    phase: Literal["accumulation", "retirement"]
    withdrawals: WithdrawalBreakdown
    benefits: BenefitBreakdown
    tax: TaxBreakdown
    after_tax_income: float
    accounts: AccountSnapshot
    warnings: list[str] = Field(default_factory=list)


class Summary(BaseModel):
    retirement_year: int
    first_retirement_after_tax_income: float
    average_retirement_after_tax_income: float
    total_after_tax_income: float
    ending_net_worth: float
    lowest_net_worth: float
    peak_taxable_income: float
    suggestions: list[str]


class SimulationResult(BaseModel):
    yearly_results: list[YearlyResult]
    summary: Summary
    warnings: list[str]
    source_version: dict[str, Any]


class ScenarioOverride(BaseModel):
    name: str
    description: str = ""
    profile: dict[str, Any] = Field(default_factory=dict)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    benefits: dict[str, Any] = Field(default_factory=dict)
    accounts: dict[str, Any] = Field(default_factory=dict)
    withdrawal_strategy: dict[str, Any] = Field(default_factory=dict)


class ScenarioComparisonRow(BaseModel):
    name: str
    description: str
    retirement_age: int
    cpp_start_age: int
    oas_start_age: int
    first_retirement_after_tax_income: float
    average_retirement_after_tax_income: float
    ending_net_worth: float
    warnings: list[str]


class ScenarioComparison(BaseModel):
    comparison_table: list[ScenarioComparisonRow]
    best_scenario: str


class OptimizeRequest(BaseModel):
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    goal: Literal["maximize_after_tax", "preserve_net_worth"] = "maximize_after_tax"


class OptimizeResponse(BaseModel):
    optimized_config: SimulationConfig
    suggestions: list[str]
    comparison: ScenarioComparison

from retirement_calculator.models import SimulationConfig
from retirement_calculator.simulator import simulate


def test_default_golden_scenario_runs_to_age_100():
    result = simulate(SimulationConfig())
    assert result.yearly_results[0].age == 40
    assert result.yearly_results[-1].age == 100
    assert result.summary.retirement_year == 2051
    assert result.summary.summary_end_age == 95
    assert result.summary.first_retirement_after_tax_income > 0
    assert result.summary.average_retirement_after_tax_income > 0
    assert "policy_year" in result.source_version


def test_account_balances_roll_forward():
    cfg = SimulationConfig()
    result = simulate(cfg)
    age_41 = result.yearly_results[1]
    assert age_41.accounts.tfsa == 58_320
    assert age_41.accounts.rrsp > cfg.accounts.rrsp.balance
    assert age_41.accounts.non_registered == 58_320


def test_oas_cpp_warning_for_age_71_start():
    result = simulate(SimulationConfig())
    assert any("OAS start age" in warning for warning in result.warnings)
    assert any("CPP start age" in warning for warning in result.warnings)


def test_life_expectancy_limits_summary_not_projection():
    cfg = SimulationConfig()
    result = simulate(cfg)
    age_95 = next(row for row in result.yearly_results if row.age == 95)
    assert result.yearly_results[-1].age == 100
    assert result.summary.ending_net_worth == age_95.accounts.net_worth


def test_legacy_investment_loan_balance_input_maps_to_new_fields():
    cfg = SimulationConfig.model_validate({"accounts": {"investment_loan": {"balance": 123_000}}})
    assert cfg.accounts.investment_loan.gross_asset_balance == 123_000
    assert cfg.accounts.investment_loan.loan_balance == 123_000


def test_tfsa_limit_and_spouse_rrsp_warnings():
    cfg = SimulationConfig.model_validate(
        {
            "accounts": {
                "tfsa": {"balance": 50_000, "annual_contribution": 9_000},
                "spouse_rrsp": {"balance": 300_000},
            }
        }
    )
    result = simulate(cfg)
    assert any("TFSA annual contribution exceeds" in warning for warning in result.warnings)
    assert any("Spouse RRSP is modeled" in warning for warning in result.warnings)

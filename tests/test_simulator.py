from retirement_calculator.models import SimulationConfig
from retirement_calculator.simulator import simulate


def test_default_golden_scenario_runs_to_age_100():
    result = simulate(SimulationConfig())
    assert result.yearly_results[0].age == 40
    assert result.yearly_results[-1].age == 100
    assert result.summary.retirement_year == 2051
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

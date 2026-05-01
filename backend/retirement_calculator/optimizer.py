from __future__ import annotations

from copy import deepcopy

from .config import apply_scenario
from .models import (
    OptimizeResponse,
    ScenarioComparison,
    ScenarioComparisonRow,
    ScenarioOverride,
    SimulationConfig,
)
from .simulator import simulate


def compare_scenarios(
    base_config: SimulationConfig,
    scenarios: list[ScenarioOverride],
) -> ScenarioComparison:
    rows: list[ScenarioComparisonRow] = []
    for scenario in scenarios:
        scenario_config = apply_scenario(base_config, scenario)
        result = simulate(scenario_config)
        rows.append(
            ScenarioComparisonRow(
                name=scenario.name,
                description=scenario.description,
                retirement_age=scenario_config.profile.retirement_age,
                cpp_start_age=scenario_config.benefits.cpp.start_age,
                oas_start_age=scenario_config.benefits.oas.start_age,
                first_retirement_after_tax_income=result.summary.first_retirement_after_tax_income,
                average_retirement_after_tax_income=result.summary.average_retirement_after_tax_income,
                ending_net_worth=result.summary.ending_net_worth,
                warnings=result.warnings,
            )
        )

    best = max(
        rows,
        key=lambda row: (row.average_retirement_after_tax_income, row.ending_net_worth),
        default=None,
    )
    return ScenarioComparison(
        comparison_table=rows,
        best_scenario=best.name if best else "",
    )


def optimize(config: SimulationConfig, goal: str = "maximize_after_tax") -> OptimizeResponse:
    scenarios = [
        ScenarioOverride(
            name="Retire 65, benefits 70",
            description="Keep age 65 retirement and cap OAS/CPP deferral at age 70.",
            profile={"retirement_age": 65},
            benefits={"oas_start_age": 70, "cpp_start_age": 70},
        ),
        ScenarioOverride(
            name="Retire 67, benefits 70",
            description="Work two extra years and defer benefits to age 70.",
            profile={"retirement_age": 67},
            benefits={"oas_start_age": 70, "cpp_start_age": 70},
        ),
        ScenarioOverride(
            name="Retire 63, benefits 65",
            description="Earlier retirement with benefits starting at 65.",
            profile={"retirement_age": 63},
            benefits={"oas_start_age": 65, "cpp_start_age": 65},
        ),
    ]
    comparison = compare_scenarios(config, scenarios)
    best_row = next(
        row for row in comparison.comparison_table if row.name == comparison.best_scenario
    )
    best_scenario = next(scenario for scenario in scenarios if scenario.name == best_row.name)
    optimized_config = apply_scenario(deepcopy(config), best_scenario)
    result = simulate(optimized_config)

    suggestions = [
        f"Best tested scenario for {goal}: {comparison.best_scenario}.",
        *result.summary.suggestions,
    ]
    return OptimizeResponse(
        optimized_config=optimized_config,
        suggestions=suggestions,
        comparison=comparison,
    )

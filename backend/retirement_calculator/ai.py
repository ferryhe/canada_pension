from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any, Literal

from openai import OpenAI

from .models import ScenarioOverride, SimulationConfig
from .optimizer import compare_scenarios, optimize
from .settings import settings
from .simulator import simulate

logger = logging.getLogger(__name__)

ChatIntent = Literal[
    "collect_info",
    "simulate",
    "adjust",
    "compare",
    "optimize",
    "report",
    "explain",
]

SYSTEM_PROMPT = """You are a Canadian retirement planning assistant for Ontario 2026.
Use function tools for simulations, comparisons, optimizations, and report export actions.
Never invent or alter financial calculation results outside tool outputs.
If the user is only starting and has not confirmed defaults or supplied facts,
ask a concise follow-up.
Explain that results are educational planning estimates, not financial advice.
"""


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


NULLABLE_NUMBER = {"type": ["number", "null"]}
NULLABLE_INTEGER = {"type": ["integer", "null"]}

CONFIG_SCHEMA = _object_schema(
    {
        "profile": _object_schema(
            {
                "current_age": {"type": "integer"},
                "retirement_age": {"type": "integer"},
                "life_expectancy": {"type": "integer"},
                "projection_end_age": {"type": "integer"},
            }
        ),
        "accounts": _object_schema(
            {
                "tfsa": _object_schema(
                    {"balance": {"type": "number"}, "annual_contribution": {"type": "number"}}
                ),
                "rrsp": _object_schema(
                    {"balance": {"type": "number"}, "annual_contribution": {"type": "number"}}
                ),
                "non_registered": _object_schema(
                    {"balance": {"type": "number"}, "annual_contribution": {"type": "number"}}
                ),
                "investment_loan": _object_schema(
                    {
                        "gross_asset_balance": {"type": "number"},
                        "loan_balance": {"type": "number"},
                        "annual_repayment": {"type": "number"},
                        "interest_rate": {"type": "number"},
                    }
                ),
                "spouse_rrsp": _object_schema(
                    {"balance": {"type": "number"}, "annual_contribution": {"type": "number"}}
                ),
            }
        ),
        "assumptions": _object_schema(
            {
                "annual_return": {"type": "number"},
                "inflation": {"type": "number"},
                "oas_cpp_growth": {"type": "number"},
            }
        ),
        "benefits": _object_schema(
            {
                "oas": _object_schema(
                    {"start_age": {"type": "integer"}, "annual_amount": {"type": "number"}}
                ),
                "cpp": _object_schema(
                    {"start_age": {"type": "integer"}, "annual_amount": {"type": "number"}}
                ),
                "gis": _object_schema(
                    {
                        "enabled": {"type": "boolean"},
                        "annual_max": {"type": "number"},
                        "income_cutoff": {"type": "number"},
                    }
                ),
            }
        ),
        "tax": _object_schema(
            {
                "province": {"type": "string", "enum": ["ON"]},
                "capital_gains_inclusion_rate": {"type": "number"},
            }
        ),
        "withdrawal_strategy": _object_schema(
            {
                "tfsa_rate": {"type": "number"},
                "non_registered_rate": {"type": "number"},
                "capital_gain_ratio": {"type": "number"},
                "spouse_rrsp_rate": {"type": "number"},
            }
        ),
    }
)

SCENARIO_INPUT_SCHEMA = _object_schema(
    {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "retirement_age": NULLABLE_INTEGER,
        "oas_start_age": NULLABLE_INTEGER,
        "cpp_start_age": NULLABLE_INTEGER,
        "annual_return": NULLABLE_NUMBER,
    }
)

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "simulate_retirement",
        "description": "Run a deterministic Ontario 2026 retirement simulation with a full config.",
        "parameters": _object_schema({"config": CONFIG_SCHEMA}),
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_retirement_scenarios",
        "description": "Compare named retirement scenarios against a full base config.",
        "parameters": _object_schema(
            {
                "config": CONFIG_SCHEMA,
                "scenarios": {"type": "array", "items": SCENARIO_INPUT_SCHEMA},
            }
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "optimize_retirement_plan",
        "description": "Try deterministic optimization candidates for a full config.",
        "parameters": _object_schema(
            {
                "config": CONFIG_SCHEMA,
                "goal": {"type": "string", "enum": ["maximize_after_tax", "preserve_net_worth"]},
            }
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "prepare_report_action",
        "description": (
            "Prepare a UI action to export the latest deterministic result as HTML or PDF."
        ),
        "parameters": _object_schema({"format": {"type": "string", "enum": ["html", "pdf"]}}),
        "strict": True,
    },
]


def chat(messages: list[dict[str, str]], config: SimulationConfig | None = None) -> dict[str, Any]:
    base_config = config or SimulationConfig()
    if not settings.openai_api_key:
        return _fallback_chat(messages, base_config)

    client = OpenAI(api_key=settings.openai_api_key)
    input_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Current full SimulationConfig JSON. Reuse this as the base and pass a full "
                f"updated config to calculation tools:\n{base_config.model_dump_json()}"
            ),
        },
        *messages,
    ]
    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=input_messages,
            tools=TOOLS,
            parallel_tool_calls=False,
            reasoning={"effort": "low"},
        )
    except Exception:
        logger.warning("OpenAI request failed; using local fallback", exc_info=True)
        fallback = _fallback_chat(messages, base_config)
        fallback["warnings"].append("OpenAI request failed; used local deterministic fallback.")
        return fallback

    tool_outputs = []
    calculations: list[dict[str, Any]] = []
    actions: list[dict[str, str]] = []
    warnings: list[str] = []
    intent: ChatIntent = "explain"
    applied_config = base_config

    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "function_call":
            continue
        execution = _execute_tool(item.name, json.loads(item.arguments or "{}"), base_config)
        intent = execution["intent"]
        applied_config = execution["applied_config"]
        warnings.extend(execution["warnings"])
        actions.extend(execution["actions"])
        if execution["calculation"] is not None:
            calculations.append({"tool": item.name, "output": execution["calculation"]})
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(execution["tool_output"], ensure_ascii=False),
            }
        )

    text = getattr(response, "output_text", "") or ""
    if tool_outputs:
        try:
            final = client.responses.create(
                model=settings.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
            )
            text = getattr(final, "output_text", "") or text
        except Exception:
            logger.warning("OpenAI final response failed after tool execution", exc_info=True)
            warnings.append("OpenAI final response failed after tool execution.")

    if not text:
        text = _default_message(intent, calculations, actions)

    return _chat_response(
        message=text,
        intent=intent,
        model=settings.openai_model,
        applied_config=applied_config,
        calculations=calculations,
        actions=actions,
        warnings=warnings,
    )


def _execute_tool(
    name: str,
    args: dict[str, Any],
    base_config: SimulationConfig,
) -> dict[str, Any]:
    if name == "simulate_retirement":
        cfg = SimulationConfig.model_validate(args["config"])
        result = simulate(cfg)
        return _tool_execution(
            intent="simulate",
            applied_config=cfg,
            calculation=result.model_dump(),
            tool_output=result.model_dump(),
            warnings=result.warnings,
        )

    if name == "compare_retirement_scenarios":
        cfg = SimulationConfig.model_validate(args["config"])
        scenarios = _scenario_inputs_to_overrides(args["scenarios"])
        comparison = compare_scenarios(cfg, scenarios)
        return _tool_execution(
            intent="compare",
            applied_config=cfg,
            calculation=comparison.model_dump(),
            tool_output=comparison.model_dump(),
            warnings=[warning for row in comparison.comparison_table for warning in row.warnings],
        )

    if name == "optimize_retirement_plan":
        cfg = SimulationConfig.model_validate(args["config"])
        optimization = optimize(cfg, args["goal"])
        return _tool_execution(
            intent="optimize",
            applied_config=optimization.optimized_config,
            calculation=optimization.model_dump(),
            tool_output=optimization.model_dump(),
            warnings=[],
        )

    if name == "prepare_report_action":
        fmt = args.get("format", "pdf")
        return _tool_execution(
            intent="report",
            applied_config=base_config,
            calculation=None,
            tool_output={"actions": [{"type": "report", "format": fmt}]},
            actions=[{"type": "report", "format": fmt}],
            warnings=[],
        )

    raise ValueError(f"Unknown tool: {name}")


def _tool_execution(
    intent: ChatIntent,
    applied_config: SimulationConfig,
    calculation: dict[str, Any] | None,
    tool_output: dict[str, Any],
    warnings: list[str],
    actions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "applied_config": applied_config,
        "calculation": calculation,
        "tool_output": tool_output,
        "warnings": warnings,
        "actions": actions or [],
    }


def _scenario_inputs_to_overrides(items: list[dict[str, Any]]) -> list[ScenarioOverride]:
    scenarios: list[ScenarioOverride] = []
    for item in items:
        profile = {}
        benefits = {}
        assumptions = {}
        if item.get("retirement_age") is not None:
            profile["retirement_age"] = item["retirement_age"]
        if item.get("oas_start_age") is not None:
            benefits["oas_start_age"] = item["oas_start_age"]
        if item.get("cpp_start_age") is not None:
            benefits["cpp_start_age"] = item["cpp_start_age"]
        if item.get("annual_return") is not None:
            assumptions["annual_return"] = item["annual_return"]
        scenarios.append(
            ScenarioOverride(
                name=item["name"],
                description=item["description"],
                profile=profile,
                benefits=benefits,
                assumptions=assumptions,
            )
        )
    return scenarios


def _fallback_chat(
    messages: list[dict[str, str]],
    config: SimulationConfig,
) -> dict[str, Any]:
    text = messages[-1]["content"] if messages else ""
    lower = text.lower()

    if _is_starter_prompt(lower):
        return _chat_response(
            message=(
                "我可以先按默认参数计算，也可以根据您的年龄、退休年龄、账户余额和收益率调整。"
                "请回复“按默认计算”，或直接写例如：40岁，RRSP50万，65退休。"
            ),
            intent="collect_info",
            model="local-fallback",
            applied_config=config,
            missing_fields=["confirm_defaults_or_profile"],
        )

    if _has_any(lower, ["导出", "pdf", "html", "报告", "report"]):
        fmt = "html" if "html" in lower else "pdf"
        return _chat_response(
            message=f"好的，我会为当前模拟结果准备 {fmt.upper()} 报告。",
            intent="report",
            model="local-fallback",
            applied_config=config,
            actions=[{"type": "report", "format": fmt}],
        )

    if _has_any(lower, ["为什么", "解释", "why", "clawback", "oas", "cpp", "gis", "rrif"]):
        return _chat_response(
            message=_explain(lower),
            intent="explain",
            model="local-fallback",
            applied_config=config,
        )

    parsed = _parse_message(text, config)

    if _has_any(lower, ["对比", "compare"]):
        comparison = compare_scenarios(parsed, _comparison_scenarios_from_text(lower, parsed))
        return _chat_response(
            message=f"已完成情景对比。当前最佳情景是 {comparison.best_scenario}。",
            intent="compare",
            model="local-fallback",
            applied_config=parsed,
            calculations=[
                {"tool": "compare_retirement_scenarios", "output": comparison.model_dump()}
            ],
            warnings=[warning for row in comparison.comparison_table for warning in row.warnings],
        )

    if _has_any(lower, ["优化", "建议", "optimize"]):
        optimization = optimize(parsed)
        return _chat_response(
            message=f"已完成优化测试。建议优先看 {optimization.comparison.best_scenario}。",
            intent="optimize",
            model="local-fallback",
            applied_config=optimization.optimized_config,
            calculations=[
                {"tool": "optimize_retirement_plan", "output": optimization.model_dump()}
            ],
        )

    result = simulate(parsed)
    intent: ChatIntent = "adjust" if parsed != config else "simulate"
    message = (
        "已按官方 2026 安省规则完成模拟。"
        f"退休首年税后现金流约 ${result.summary.first_retirement_after_tax_income:,.0f}，"
        f"到 {result.summary.summary_end_age} 岁前的退休期平均约 "
        f"${result.summary.average_retirement_after_tax_income:,.0f}。"
    )
    return _chat_response(
        message=message,
        intent=intent,
        model="local-fallback",
        applied_config=parsed,
        calculations=[{"tool": "simulate_retirement", "output": result.model_dump()}],
        warnings=result.warnings,
    )


def _parse_message(text: str, base: SimulationConfig) -> SimulationConfig:
    data = deepcopy(base.model_dump())
    lower = text.lower()

    age_match = re.search(r"(\d{2})\s*(?:岁|years? old|yo)", lower)
    if age_match:
        data["profile"]["current_age"] = int(age_match.group(1))

    retire_match = re.search(r"(\d{2})\s*(?:岁)?\s*(?:退休|retire)", lower)
    if retire_match:
        data["profile"]["retirement_age"] = int(retire_match.group(1))

    life_match = re.search(r"(\d{2,3})\s*(?:岁)?\s*(?:寿命|life|expectancy|活到)", lower)
    if life_match:
        data["profile"]["life_expectancy"] = int(life_match.group(1))

    percent_match = re.search(r"(?:收益|return|年化)\D*(\d+(?:\.\d+)?)\s*%", lower)
    if percent_match:
        data["assumptions"]["annual_return"] = float(percent_match.group(1)) / 100
    elif "5%" in lower or "0.05" in lower:
        data["assumptions"]["annual_return"] = 0.05

    inflation_match = re.search(r"(?:通胀|inflation)\D*(\d+(?:\.\d+)?)\s*%", lower)
    if inflation_match:
        data["assumptions"]["inflation"] = float(inflation_match.group(1)) / 100

    account_patterns = {
        ("accounts", "rrsp", "balance"): r"rrsp\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?",
        ("accounts", "tfsa", "balance"): r"tfsa\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?",
        ("accounts", "non_registered", "balance"): (
            r"(?:non[- ]?registered|非注册)\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?"
        ),
        ("accounts", "spouse_rrsp", "balance"): (
            r"(?:spouse rrsp|配偶\s*rrsp)\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?"
        ),
        ("accounts", "investment_loan", "loan_balance"): (
            r"(?:loan|贷款)\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?"
        ),
    }
    for path, pattern in account_patterns.items():
        match = re.search(pattern, lower)
        if not match:
            continue
        _set_nested(data, path, _parse_amount(match.group(1), match.group(2)))
        if path == ("accounts", "investment_loan", "loan_balance"):
            _set_nested(
                data,
                ("accounts", "investment_loan", "gross_asset_balance"),
                _parse_amount(match.group(1), match.group(2)),
            )

    benefit_patterns = {
        ("benefits", "oas", "start_age"): r"oas\s*(?:起始|start|@)?\D*(\d{2})",
        ("benefits", "cpp", "start_age"): r"cpp\s*(?:起始|start|@)?\D*(\d{2})",
    }
    for path, pattern in benefit_patterns.items():
        match = re.search(pattern, lower)
        if match:
            _set_nested(data, path, int(match.group(1)))

    return SimulationConfig.model_validate(data)


def _comparison_scenarios_from_text(
    lower: str,
    config: SimulationConfig,
) -> list[ScenarioOverride]:
    retire_ages = [int(match) for match in re.findall(r"(\d{2})\s*(?:岁)?\s*退休", lower)]
    if not retire_ages:
        retire_ages = [config.profile.retirement_age, 67]
    scenarios = [
        ScenarioOverride(
            name=f"Retire {age}",
            description=f"Retirement age {age}",
            profile={"retirement_age": age},
            benefits={
                "oas_start_age": min(config.benefits.oas.start_age, 70),
                "cpp_start_age": min(config.benefits.cpp.start_age, 70),
            },
        )
        for age in sorted(set(retire_ages))
    ]
    if len(scenarios) == 1:
        scenarios.insert(
            0,
            ScenarioOverride(
                name="Current",
                description="Current configuration",
                profile={"retirement_age": config.profile.retirement_age},
            ),
        )
    return scenarios


def _chat_response(
    message: str,
    intent: ChatIntent,
    model: str,
    applied_config: SimulationConfig,
    calculations: list[dict[str, Any]] | None = None,
    actions: list[dict[str, str]] | None = None,
    missing_fields: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "message": message,
        "intent": intent,
        "model": model,
        "applied_config": applied_config.model_dump(),
        "calculations": calculations or [],
        "actions": actions or [],
        "missing_fields": missing_fields or [],
        "warnings": list(dict.fromkeys(warnings or [])),
    }


def _default_message(
    intent: ChatIntent,
    calculations: list[dict[str, Any]],
    actions: list[dict[str, str]],
) -> str:
    if intent == "report" and actions:
        return f"Report export is ready as {actions[0]['format'].upper()}."
    if calculations:
        return "Calculation complete. Please review the deterministic results."
    return "What would you like to simulate?"


def _is_starter_prompt(lower: str) -> bool:
    return _has_any(lower, ["帮我规划退休", "规划退休", "开始", "hello"]) and not _has_any(
        lower,
        ["默认", "rrsp", "tfsa", "退休年龄", "retire", "岁"],
    )


def _explain(lower: str) -> str:
    if "oas" in lower or "延迟" in lower:
        return "OAS 可以延迟领取，但官方延迟增幅最多计算到 70 岁；70 岁后再延迟只会推迟现金流。"
    if "cpp" in lower:
        return "CPP 在 65 岁为基准，提前会减少，延迟到 70 岁前会增加；本工具按官方延迟上限封顶。"
    if "gis" in lower:
        return "GIS 是低收入补助，和其他应税收入反向相关；RRSP/RRIF 提取、CPP 等收入会降低 GIS。"
    if "rrif" in lower:
        return "RRSP 通常在 71 岁转入 RRIF；本工具按 CRA 最低提取比例模拟 RRIF 提款。"
    return "本工具用官方 2026 安省/联邦税务和福利假设做教育性估算，计算结果都来自后端确定性函数。"


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _set_nested(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor = data
    for segment in path[:-1]:
        cursor = cursor[segment]
    cursor[path[-1]] = value


def _parse_amount(raw: str, suffix: str | None) -> float:
    value = float(raw.replace(",", ""))
    if suffix == "万":
        return value * 10_000
    if suffix == "k":
        return value * 1_000
    return value

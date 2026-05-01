from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .models import ScenarioOverride, SimulationConfig
from .optimizer import compare_scenarios, optimize
from .settings import settings
from .simulator import simulate

SYSTEM_PROMPT = """You are a Canadian retirement planning assistant.
Use tools for every calculation. Never invent financial results.
Ask concise follow-up questions when required fields are missing.
Explain that results are educational planning estimates, not financial advice.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "simulate_retirement",
            "description": "Run a deterministic Ontario 2026 retirement simulation.",
            "parameters": SimulationConfig.model_json_schema(),
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_retirement_scenarios",
            "description": "Compare named retirement scenarios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config": SimulationConfig.model_json_schema(),
                    "scenarios": {
                        "type": "array",
                        "items": ScenarioOverride.model_json_schema(),
                    },
                },
                "required": ["config", "scenarios"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_retirement_plan",
            "description": "Try a small deterministic optimization set.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config": SimulationConfig.model_json_schema(),
                    "goal": {
                        "type": "string",
                        "enum": ["maximize_after_tax", "preserve_net_worth"],
                    },
                },
                "required": ["config", "goal"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]


def chat(messages: list[dict[str, str]], config: SimulationConfig | None = None) -> dict[str, Any]:
    if not settings.openai_api_key:
        return _fallback_chat(messages, config)

    client = OpenAI(api_key=settings.openai_api_key)
    input_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    response = client.responses.create(
        model=settings.openai_model,
        input=input_messages,
        tools=TOOLS,
        reasoning={"effort": "low"},
    )

    tool_outputs = []
    calculations: list[dict[str, Any]] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "function_call":
            continue
        name = item.name
        args = json.loads(item.arguments or "{}")
        output = _call_tool(name, args)
        calculations.append({"tool": name, "output": output})
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(output, ensure_ascii=False),
            }
        )

    if tool_outputs:
        final = client.responses.create(
            model=settings.openai_model,
            previous_response_id=response.id,
            input=tool_outputs,
        )
        text = getattr(final, "output_text", "") or "Simulation complete."
    else:
        text = getattr(response, "output_text", "") or "What would you like to simulate?"

    return {"message": text, "calculations": calculations, "model": settings.openai_model}


def _call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "simulate_retirement":
        result = simulate(SimulationConfig.model_validate(args))
        return result.model_dump()
    if name == "compare_retirement_scenarios":
        base = SimulationConfig.model_validate(args["config"])
        scenarios = [ScenarioOverride.model_validate(item) for item in args["scenarios"]]
        return compare_scenarios(base, scenarios).model_dump()
    if name == "optimize_retirement_plan":
        base = SimulationConfig.model_validate(args["config"])
        return optimize(base, args.get("goal", "maximize_after_tax")).model_dump()
    raise ValueError(f"Unknown tool: {name}")


def _fallback_chat(
    messages: list[dict[str, str]],
    config: SimulationConfig | None,
) -> dict[str, Any]:
    text = messages[-1]["content"] if messages else ""
    parsed = _parse_message(text, config or SimulationConfig())
    result = simulate(parsed)
    message = (
        "已用本地规则解析并完成模拟。"
        f"退休首年税后现金流约 ${result.summary.first_retirement_after_tax_income:,.0f}，"
        f"退休期平均约 ${result.summary.average_retirement_after_tax_income:,.0f}。"
    )
    return {
        "message": message,
        "calculations": [{"tool": "simulate_retirement", "output": result.model_dump()}],
        "model": "local-fallback",
    }


def _parse_message(text: str, base: SimulationConfig) -> SimulationConfig:
    data = base.model_dump()
    lower = text.lower()

    age_match = re.search(r"(\d{2})\s*(?:岁|years? old|yo)", lower)
    if age_match:
        data["profile"]["current_age"] = int(age_match.group(1))

    retire_match = re.search(r"(\d{2})\s*(?:岁)?\s*(?:退休|retire)", lower)
    if retire_match:
        data["profile"]["retirement_age"] = int(retire_match.group(1))

    account_patterns = {
        "rrsp": r"rrsp\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?",
        "tfsa": r"tfsa\s*(?:有|:|=)?\s*\$?\s*([\d,.]+)\s*(万|k)?",
    }
    for account, pattern in account_patterns.items():
        match = re.search(pattern, lower)
        if match:
            data["accounts"][account]["balance"] = _parse_amount(match.group(1), match.group(2))

    if "5%" in lower or "0.05" in lower:
        data["assumptions"]["annual_return"] = 0.05

    return SimulationConfig.model_validate(data)


def _parse_amount(raw: str, suffix: str | None) -> float:
    value = float(raw.replace(",", ""))
    if suffix == "万":
        return value * 10_000
    if suffix == "k":
        return value * 1_000
    return value

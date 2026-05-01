from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .models import ScenarioOverride, SimulationConfig


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_mapping(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def load_config(path: str | Path) -> SimulationConfig:
    data = load_mapping(path)
    if data.get("tax", {}).get("province") is True:
        data["tax"]["province"] = "ON"
    return SimulationConfig.model_validate(data)


def load_scenarios(path: str | Path) -> list[ScenarioOverride]:
    data = load_mapping(path)
    return [ScenarioOverride.model_validate(item) for item in data.get("scenarios", [])]


def apply_scenario(base_config: SimulationConfig, scenario: ScenarioOverride) -> SimulationConfig:
    data = base_config.model_dump()

    direct_override = {
        "profile": scenario.profile,
        "assumptions": scenario.assumptions,
        "accounts": scenario.accounts,
        "withdrawal_strategy": scenario.withdrawal_strategy,
    }
    data = deep_merge(data, {key: value for key, value in direct_override.items() if value})

    if scenario.benefits:
        benefit_override: dict[str, Any] = {}
        if "oas_start_age" in scenario.benefits:
            benefit_override.setdefault("oas", {})["start_age"] = scenario.benefits["oas_start_age"]
        if "cpp_start_age" in scenario.benefits:
            benefit_override.setdefault("cpp", {})["start_age"] = scenario.benefits["cpp_start_age"]
        for key in ("oas", "cpp", "gis"):
            if key in scenario.benefits:
                benefit_override[key] = deep_merge(
                    benefit_override.get(key, {}),
                    scenario.benefits[key],
                )
        data = deep_merge(data, {"benefits": benefit_override})

    return SimulationConfig.model_validate(data)

import os

import pytest
from retirement_calculator.ai import chat
from retirement_calculator.models import SimulationConfig
from retirement_calculator.settings import settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_OPENAI") != "1" or not settings.openai_api_key,
    reason="Set RUN_LIVE_OPENAI=1 and OPENAI_API_KEY to run live OpenAI smoke tests.",
)


@pytest.mark.parametrize(
    "prompt",
    [
        "按默认计算",
        "收益率改成5%重新算",
        "和67岁退休对比",
        "导出PDF",
        "为什么OAS延迟到70岁",
    ],
)
def test_live_openai_chat_smoke(prompt):
    response = chat([{"role": "user", "content": prompt}], SimulationConfig())

    assert response["model"] == settings.openai_model
    assert response["intent"] in {
        "collect_info",
        "simulate",
        "adjust",
        "compare",
        "optimize",
        "report",
        "explain",
    }
    assert response["message"]
    assert isinstance(response["calculations"], list)
    actions = response.get("actions") or []
    assert isinstance(actions, list)
    if actions:
        assert any(
            action.get("type") == "report" and action.get("format") in {"html", "pdf"}
            for action in actions
            if isinstance(action, dict)
        )

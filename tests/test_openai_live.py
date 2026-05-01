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
    ("prompt", "expected"),
    [
        ("按默认计算", "simulate"),
        ("收益率改成5%重新算", "simulate"),
        ("和67岁退休对比", "compare"),
        ("导出PDF", "report"),
        ("为什么OAS延迟到70岁", "explain"),
    ],
)
def test_live_openai_chat_smoke(prompt, expected):
    response = chat([{"role": "user", "content": prompt}], SimulationConfig())

    assert response["model"] == settings.openai_model
    assert response["intent"] == expected
    assert response["message"]
    if expected in {"simulate", "compare"}:
        assert response["calculations"]
    if expected == "report":
        assert response["actions"] == [{"type": "report", "format": "pdf"}]

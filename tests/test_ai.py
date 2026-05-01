import json
from types import SimpleNamespace

from retirement_calculator import ai
from retirement_calculator.models import SimulationConfig


def test_responses_function_tools_use_current_shape():
    tool = ai.TOOLS[0]
    assert tool["type"] == "function"
    assert tool["name"] == "simulate_retirement"
    assert "function" not in tool
    assert tool["strict"] is True
    assert tool["parameters"]["additionalProperties"] is False


def test_openai_chat_uses_tool_outputs(monkeypatch):
    cfg = SimulationConfig()
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                assert kwargs["tools"][0]["name"] == "simulate_retirement"
                assert kwargs["parallel_tool_calls"] is False
                return SimpleNamespace(
                    id="resp_1",
                    output=[
                        SimpleNamespace(
                            type="function_call",
                            name="simulate_retirement",
                            arguments=json.dumps({"config": cfg.model_dump()}),
                            call_id="call_1",
                        )
                    ],
                    output_text="",
                )
            assert kwargs["input"][0]["type"] == "function_call_output"
            return SimpleNamespace(output_text="已完成官方模拟。")

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.responses = FakeResponses()

    monkeypatch.setattr(ai.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(ai, "OpenAI", FakeClient)

    response = ai.chat([{"role": "user", "content": "按默认计算"}], cfg)

    assert response["model"] == ai.settings.openai_model
    assert response["intent"] == "simulate"
    assert response["message"] == "已完成官方模拟。"
    assert response["calculations"][0]["tool"] == "simulate_retirement"
    assert response["calculations"][0]["output"]["summary"]["summary_end_age"] == 95

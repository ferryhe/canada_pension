from fastapi.testclient import TestClient
from retirement_calculator.api import app
from retirement_calculator.models import SimulationConfig
from retirement_calculator.simulator import simulate

client = TestClient(app)


def test_simulate_endpoint():
    response = client.post("/api/v1/simulate", json={"config": SimulationConfig().model_dump()})
    assert response.status_code == 200
    assert response.json()["summary"]["retirement_year"] == 2051


def test_compare_endpoint():
    response = client.post(
        "/api/v1/compare",
        json={
            "config": SimulationConfig().model_dump(),
            "scenarios": [
                {"name": "Base", "profile": {"retirement_age": 65}},
                {"name": "Later", "profile": {"retirement_age": 67}},
            ],
        },
    )
    assert response.status_code == 200
    assert len(response.json()["comparison_table"]) == 2
    assert response.json()["best_scenario"] in {"Base", "Later"}


def test_optimize_endpoint():
    response = client.post("/api/v1/optimize", json={"config": SimulationConfig().model_dump()})
    assert response.status_code == 200
    assert response.json()["suggestions"]


def test_report_html_endpoint():
    result = simulate(SimulationConfig())
    response = client.post(
        "/api/v1/report",
        json={"result": result.model_dump(), "format": "html", "template": "summary"},
    )
    assert response.status_code == 200
    assert "Retirement Summary" in response.text


def test_report_pdf_dependency_error(monkeypatch):
    def unavailable_pdf(_html):
        raise RuntimeError("WeasyPrint is not available in this environment")

    monkeypatch.setattr("retirement_calculator.api.render_pdf", unavailable_pdf)
    result = simulate(SimulationConfig())
    response = client.post(
        "/api/v1/report",
        json={"result": result.model_dump(), "format": "pdf", "template": "summary"},
    )
    assert response.status_code == 503
    assert "WeasyPrint is not available" in response.json()["detail"]


def test_chat_falls_back_without_openai_key(monkeypatch):
    monkeypatch.setattr("retirement_calculator.ai.settings.openai_api_key", None)
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "40岁，RRSP50万，65退休"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "local-fallback"
    assert body["intent"] in {"simulate", "adjust"}
    assert body["applied_config"]["accounts"]["rrsp"]["balance"] == 500_000
    assert body["calculations"][0]["tool"] == "simulate_retirement"


def test_chat_report_action_without_openai_key(monkeypatch):
    monkeypatch.setattr("retirement_calculator.ai.settings.openai_api_key", None)
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "导出PDF"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "report"
    assert body["actions"] == [{"type": "report", "format": "pdf"}]


def test_chat_compare_without_openai_key(monkeypatch):
    monkeypatch.setattr("retirement_calculator.ai.settings.openai_api_key", None)
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "和67岁退休对比下"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "compare"
    assert body["calculations"][0]["tool"] == "compare_retirement_scenarios"


def test_chat_collects_missing_profile_confirmation(monkeypatch):
    monkeypatch.setattr("retirement_calculator.ai.settings.openai_api_key", None)
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "帮我规划退休"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "collect_info"
    assert body["missing_fields"] == ["confirm_defaults_or_profile"]

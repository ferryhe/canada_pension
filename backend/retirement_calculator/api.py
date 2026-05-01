from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .ai import chat
from .models import OptimizeRequest, ScenarioOverride, SimulationConfig, SimulationResult
from .optimizer import compare_scenarios, optimize
from .output import render_pdf, render_result_html
from .settings import settings
from .simulator import simulate

app = FastAPI(title="Canada Retirement Planner", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class CompareRequest(BaseModel):
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    scenarios: list[ScenarioOverride]


class ReportRequest(BaseModel):
    result: SimulationResult
    template: Literal["summary", "detailed"] = "summary"
    format: Literal["html", "pdf"] = "html"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    config: SimulationConfig | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/simulate")
def simulate_endpoint(request: SimulateRequest) -> SimulationResult:
    return simulate(request.config)


@app.post("/api/v1/compare")
def compare_endpoint(request: CompareRequest):
    return compare_scenarios(request.config, request.scenarios)


@app.post("/api/v1/optimize")
def optimize_endpoint(request: OptimizeRequest):
    return optimize(request.config, request.goal)


@app.post("/api/v1/chat")
def chat_endpoint(request: ChatRequest):
    return chat([message.model_dump() for message in request.messages], request.config)


@app.post("/api/v1/report")
def report_endpoint(request: ReportRequest):
    html = render_result_html(request.result, request.template)
    if request.format == "pdf":
        return Response(render_pdf(html), media_type="application/pdf")
    return HTMLResponse(html)


@app.get("/api/v1/templates")
def templates() -> dict[str, list[str]]:
    return {"templates": ["summary", "detailed", "comparison"]}

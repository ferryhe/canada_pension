from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .models import ScenarioComparison, SimulationResult

env = Environment(
    loader=PackageLoader("retirement_calculator", "templates"),
    autoescape=select_autoescape(["html"]),
)


def result_from_json(path: str | Path) -> SimulationResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SimulationResult.model_validate(data)


def render_result_html(result: SimulationResult, template: str = "summary") -> str:
    template_obj = env.get_template(f"{template}.html")
    return template_obj.render(result=result)


def render_comparison_html(comparison: ScenarioComparison) -> str:
    template_obj = env.get_template("comparison.html")
    return template_obj.render(comparison=comparison)


def render_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover - depends on system libraries
        raise RuntimeError("WeasyPrint is not available in this environment") from exc
    try:
        return HTML(string=html).write_pdf()
    except Exception as exc:  # pragma: no cover - depends on system libraries
        raise RuntimeError("WeasyPrint is not available in this environment") from exc


def write_report(
    result: SimulationResult,
    output_path: str | Path,
    template: str,
    fmt: str,
) -> Path:
    destination = Path(output_path)
    html = render_result_html(result, template)
    if fmt == "html":
        destination.write_text(html, encoding="utf-8")
    elif fmt == "pdf":
        destination.write_bytes(render_pdf(html))
    else:
        raise ValueError("fmt must be html or pdf")
    return destination

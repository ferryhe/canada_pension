from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from .config import load_config, load_scenarios
from .models import SimulationConfig
from .optimizer import compare_scenarios
from .output import result_from_json, write_report
from .simulator import simulate as run_simulation

app = typer.Typer(help="Canadian retirement planning CLI.")


@app.command()
def simulate(
    config: Annotated[Path | None, typer.Option("--config", "-c")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("result.json"),
) -> None:
    simulation_config = load_config(config) if config else SimulationConfig()
    result = run_simulation(simulation_config)
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Wrote simulation to {output}")


@app.command()
def compare(
    scenarios: Annotated[Path, typer.Option("--scenarios", "-s")] = Path("scenarios.example.yaml"),
    config: Annotated[Path | None, typer.Option("--config", "-c")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("compare.json"),
) -> None:
    base_config = load_config(config) if config else SimulationConfig()
    comparison = compare_scenarios(base_config, load_scenarios(scenarios))
    output.write_text(comparison.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Wrote comparison to {output}")


@app.command()
def report(
    result: Annotated[Path, typer.Option("--result", "-r")] = Path("result.json"),
    template: Annotated[str, typer.Option("--template", "-t")] = "summary",
    format: Annotated[str, typer.Option("--format", "-f")] = "html",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    if format not in {"html", "pdf"}:
        raise typer.BadParameter("--format must be html or pdf")
    parsed = result_from_json(result)
    destination = output or Path(f"retirement-report.{format}")
    try:
        write_report(parsed, destination, template, format)
    except RuntimeError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Wrote report to {destination}")


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8000,
    reload: Annotated[bool, typer.Option("--reload")] = False,
) -> None:
    uvicorn.run("retirement_calculator.api:app", host=host, port=port, reload=reload)


@app.command()
def show_defaults() -> None:
    typer.echo(json.dumps(SimulationConfig().model_dump(), indent=2))


if __name__ == "__main__":
    app()

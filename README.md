# Canada Retirement Planner

End-to-end MVP for Ontario-based Canadian retirement planning. The app combines a
deterministic Python calculation engine with a FastAPI API, a Typer CLI, an OpenAI
tool-calling assistant layer, and a React dashboard.

## Quick Start

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -e ".[dev]"
retirement simulate --config config.example.yaml --output result.json
retirement serve
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` to enable the real assistant.
Without a key, `/api/v1/chat` falls back to a deterministic parser for local demos.

## Policy Baseline

- Canada/Ontario 2026 tax settings from CRA T4032-ON.
- OAS/CPP/GIS April-June 2026 maximums from Canada.ca.
- RRSP/TFSA/YMPE/YAMPE 2026 registered plan limits from CRA.
- RRIF minimum factors from CRA prescribed-factor guidance.

This is a planning model, not tax, legal, or financial advice.

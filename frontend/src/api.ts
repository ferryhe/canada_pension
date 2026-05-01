import type { ChatMessage, ChatResponse, ScenarioComparison, SimulationConfig, SimulationResult } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function requestJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function simulate(config: SimulationConfig): Promise<SimulationResult> {
  return requestJson<SimulationResult>("/api/v1/simulate", { config });
}

export function compare(config: SimulationConfig): Promise<ScenarioComparison> {
  return requestJson<ScenarioComparison>("/api/v1/compare", {
    config,
    scenarios: [
      { name: "Base", description: "65 retirement, 71 benefit starts" },
      {
        name: "Retire 67",
        description: "Work two extra years",
        profile: { retirement_age: 67 },
        benefits: { oas_start_age: 70, cpp_start_age: 70 }
      },
      {
        name: "Benefit 70",
        description: "Keep retirement age, cap benefits at 70",
        benefits: { oas_start_age: 70, cpp_start_age: 70 }
      }
    ]
  });
}

export function sendChat(messages: ChatMessage[], config: SimulationConfig): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/api/v1/chat", { messages, config });
}

export async function createReport(result: SimulationResult, format: "html" | "pdf"): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/v1/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result, format, template: "summary" })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.blob();
}

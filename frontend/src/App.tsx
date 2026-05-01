import {
  BarChart3,
  Bot,
  FileText,
  Loader2,
  MessageSquareText,
  Play,
  RefreshCcw,
  SlidersHorizontal
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { compare, createReport, sendChat, simulate } from "./api";
import { defaultConfig } from "./defaultConfig";
import { money, percent } from "./format";
import type { ChatMessage, ScenarioComparison, SimulationConfig, SimulationResult } from "./types";

type Status = "idle" | "loading" | "error";

const initialMessages: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "您好，我可以用安省 2026 规则模拟退休现金流。您可以直接说“按默认计算”，或修改右侧参数。"
  }
];

export function App() {
  const [config, setConfig] = useState<SimulationConfig>(defaultConfig);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("按默认计算");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [reportUrl, setReportUrl] = useState("");

  useEffect(() => {
    void runSimulation();
    return () => {
      if (reportUrl) URL.revokeObjectURL(reportUrl);
    };
  }, []);

  async function runSimulation(nextConfig = config) {
    setStatus("loading");
    setError("");
    try {
      const nextResult = await simulate(nextConfig);
      setResult(nextResult);
      setConfig(nextConfig);
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
      setStatus("error");
    }
  }

  async function runComparison() {
    setStatus("loading");
    setError("");
    try {
      setComparison(await compare(config));
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
      setStatus("error");
    }
  }

  async function submitChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setDraft("");
    setStatus("loading");
    setError("");

    try {
      const response = await sendChat(nextMessages, config);
      setMessages([...nextMessages, { role: "assistant", content: response.message }]);
      const simulation = response.calculations.find((item) => item.tool === "simulate_retirement");
      if (simulation && isSimulationResult(simulation.output)) {
        setResult(simulation.output);
      }
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant failed");
      setStatus("error");
    }
  }

  async function exportReport(format: "html" | "pdf") {
    if (!result) return;
    setStatus("loading");
    setError("");
    try {
      const blob = await createReport(result, format);
      if (reportUrl) URL.revokeObjectURL(reportUrl);
      const url = URL.createObjectURL(blob);
      setReportUrl(url);
      window.open(url, "_blank", "noopener,noreferrer");
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report export failed");
      setStatus("error");
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f4ee] text-[#17312f]">
      <div className="mx-auto flex min-h-screen max-w-[1680px] flex-col gap-4 px-4 py-4 lg:px-6">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#d8d1c4] pb-3">
          <div>
            <h1 className="text-xl font-semibold tracking-normal">Canada Retirement Planner</h1>
            <p className="text-sm text-[#5c6f6a]">Ontario 2026 · AI-assisted deterministic planning</p>
          </div>
          <div className="flex items-center gap-2">
            <ActionButton icon={<Play />} label="模拟" onClick={() => void runSimulation()} />
            <ActionButton icon={<BarChart3 />} label="对比" onClick={() => void runComparison()} />
            <ActionButton icon={<FileText />} label="PDF" onClick={() => void exportReport("pdf")} />
          </div>
        </header>

        {error && (
          <div className="rounded-md border border-[#bb5a4a] bg-[#fff7f3] px-3 py-2 text-sm text-[#8c2f22]">
            {error}
          </div>
        )}

        <section className="grid flex-1 grid-cols-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)_360px]">
          <ChatPanel
            messages={messages}
            draft={draft}
            setDraft={setDraft}
            submitChat={submitChat}
            busy={status === "loading"}
          />
          <ResultsPanel result={result} comparison={comparison} busy={status === "loading"} />
          <ConfigPanel
            config={config}
            setConfig={setConfig}
            runSimulation={runSimulation}
            reset={() => {
              setConfig(defaultConfig);
              void runSimulation(defaultConfig);
            }}
          />
        </section>
      </div>
    </main>
  );
}

function ChatPanel({
  messages,
  draft,
  setDraft,
  submitChat,
  busy
}: {
  messages: ChatMessage[];
  draft: string;
  setDraft: (value: string) => void;
  submitChat: (event: FormEvent<HTMLFormElement>) => void;
  busy: boolean;
}) {
  return (
    <section className="panel flex min-h-[560px] flex-col">
      <PanelTitle icon={<MessageSquareText />} title="AI 对话" />
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.map((message, index) => (
          <div
            className={`message ${message.role === "user" ? "message-user" : "message-assistant"}`}
            key={`${message.role}-${index}`}
          >
            <span className="message-role">{message.role === "user" ? "You" : "AI"}</span>
            <p>{message.content}</p>
          </div>
        ))}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={submitChat}>
        <input
          className="field flex-1"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="40岁，RRSP50万，65退休"
        />
        <button className="icon-button" disabled={busy} title="Send" type="submit">
          {busy ? <Loader2 className="animate-spin" /> : <Bot />}
        </button>
      </form>
    </section>
  );
}

function ResultsPanel({
  result,
  comparison,
  busy
}: {
  result: SimulationResult | null;
  comparison: ScenarioComparison | null;
  busy: boolean;
}) {
  const retirementRows = useMemo(
    () => result?.yearly_results.filter((row) => row.phase === "retirement").slice(0, 12) ?? [],
    [result]
  );
  const chartRows = useMemo(
    () => result?.yearly_results.filter((_, index) => index % 5 === 0) ?? [],
    [result]
  );
  const maxWorth = Math.max(...chartRows.map((row) => row.accounts.net_worth), 1);

  return (
    <section className="flex min-h-[560px] flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <Metric label="退休年份" value={result ? String(result.summary.retirement_year) : "--"} />
        <Metric
          label="退休首年税后"
          value={result ? money(result.summary.first_retirement_after_tax_income) : "--"}
        />
        <Metric
          label="退休期平均"
          value={result ? money(result.summary.average_retirement_after_tax_income) : "--"}
        />
        <Metric label="终值净资产" value={result ? money(result.summary.ending_net_worth) : "--"} />
      </div>

      <section className="panel">
        <PanelTitle icon={<BarChart3 />} title="资产轨迹" />
        <div className="chart" aria-label="Net worth chart">
          {chartRows.map((row) => (
            <div className="chart-column" key={row.age}>
              <span
                className="chart-bar"
                style={{ height: `${Math.max(6, (row.accounts.net_worth / maxWorth) * 100)}%` }}
                title={`${row.age}: ${money(row.accounts.net_worth)}`}
              />
              <span className="chart-label">{row.age}</span>
            </div>
          ))}
          {busy && <div className="chart-busy"><Loader2 className="animate-spin" /></div>}
        </div>
      </section>

      <section className="panel flex-1 overflow-hidden">
        <PanelTitle icon={<SlidersHorizontal />} title="退休年度" />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>年龄</th>
                <th>税后现金流</th>
                <th>应税收入</th>
                <th>税费</th>
                <th>OAS</th>
                <th>CPP</th>
                <th>净资产</th>
              </tr>
            </thead>
            <tbody>
              {retirementRows.map((row) => (
                <tr key={row.age}>
                  <td>{row.age}</td>
                  <td>{money(row.after_tax_income)}</td>
                  <td>{money(row.tax.taxable_income)}</td>
                  <td>{money(row.tax.total_tax)}</td>
                  <td>{money(row.benefits.oas)}</td>
                  <td>{money(row.benefits.cpp)}</td>
                  <td>{money(row.accounts.net_worth)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {comparison && (
        <section className="panel">
          <PanelTitle icon={<BarChart3 />} title={`情景对比 · ${comparison.best_scenario}`} />
          <div className="grid gap-2 md:grid-cols-3">
            {comparison.comparison_table.map((row) => (
              <div className="scenario" key={row.name}>
                <strong>{row.name}</strong>
                <span>{money(row.average_retirement_after_tax_income)}</span>
                <small>退休 {row.retirement_age} · CPP {row.cpp_start_age} · OAS {row.oas_start_age}</small>
              </div>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function ConfigPanel({
  config,
  setConfig,
  runSimulation,
  reset
}: {
  config: SimulationConfig;
  setConfig: (config: SimulationConfig) => void;
  runSimulation: (config: SimulationConfig) => Promise<void>;
  reset: () => void;
}) {
  function update(path: string[], value: number | boolean) {
    const next = structuredClone(config);
    let cursor: Record<string, unknown> = next as unknown as Record<string, unknown>;
    for (const segment of path.slice(0, -1)) {
      cursor = cursor[segment] as Record<string, unknown>;
    }
    cursor[path[path.length - 1]] = value;
    setConfig(next);
  }

  return (
    <section className="panel flex min-h-[560px] flex-col">
      <div className="mb-3 flex items-center justify-between">
        <PanelTitle icon={<SlidersHorizontal />} title="参数" />
        <button className="icon-button subtle" title="Reset" onClick={reset} type="button">
          <RefreshCcw />
        </button>
      </div>
      <div className="space-y-4 overflow-y-auto pr-1">
        <FieldGroup title="Profile">
          <NumberField label="当前年龄" value={config.profile.current_age} onChange={(value) => update(["profile", "current_age"], value)} />
          <NumberField label="退休年龄" value={config.profile.retirement_age} onChange={(value) => update(["profile", "retirement_age"], value)} />
          <NumberField label="模拟终点" value={config.profile.projection_end_age} onChange={(value) => update(["profile", "projection_end_age"], value)} />
        </FieldGroup>
        <FieldGroup title="Accounts">
          <NumberField label="TFSA" value={config.accounts.tfsa.balance} onChange={(value) => update(["accounts", "tfsa", "balance"], value)} />
          <NumberField label="RRSP" value={config.accounts.rrsp.balance} onChange={(value) => update(["accounts", "rrsp", "balance"], value)} />
          <NumberField label="RRSP 年供款" value={config.accounts.rrsp.annual_contribution} onChange={(value) => update(["accounts", "rrsp", "annual_contribution"], value)} />
          <NumberField label="非注册" value={config.accounts.non_registered.balance} onChange={(value) => update(["accounts", "non_registered", "balance"], value)} />
          <NumberField label="投资贷款" value={config.accounts.investment_loan.balance} onChange={(value) => update(["accounts", "investment_loan", "balance"], value)} />
          <NumberField label="配偶 RRSP" value={config.accounts.spouse_rrsp.balance} onChange={(value) => update(["accounts", "spouse_rrsp", "balance"], value)} />
        </FieldGroup>
        <FieldGroup title="Assumptions">
          <NumberField label="年化收益" step={0.01} value={config.assumptions.annual_return} format={percent} onChange={(value) => update(["assumptions", "annual_return"], value)} />
          <NumberField label="通胀" step={0.01} value={config.assumptions.inflation} format={percent} onChange={(value) => update(["assumptions", "inflation"], value)} />
          <NumberField label="OAS/CPP 增长" step={0.01} value={config.assumptions.oas_cpp_growth} format={percent} onChange={(value) => update(["assumptions", "oas_cpp_growth"], value)} />
        </FieldGroup>
        <FieldGroup title="Benefits">
          <NumberField label="OAS 起始" value={config.benefits.oas.start_age} onChange={(value) => update(["benefits", "oas", "start_age"], value)} />
          <NumberField label="CPP 起始" value={config.benefits.cpp.start_age} onChange={(value) => update(["benefits", "cpp", "start_age"], value)} />
          <label className="toggle">
            <input
              checked={config.benefits.gis.enabled}
              type="checkbox"
              onChange={(event) => update(["benefits", "gis", "enabled"], event.target.checked)}
            />
            <span>GIS</span>
          </label>
        </FieldGroup>
      </div>
      <button className="primary-action mt-4" onClick={() => void runSimulation(config)} type="button">
        <Play />
        Run
      </button>
    </section>
  );
}

function FieldGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="field-group">
      <legend>{title}</legend>
      {children}
    </fieldset>
  );
}

function NumberField({
  label,
  value,
  onChange,
  step = 1,
  format
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: number;
  format?: (value: number) => string;
}) {
  return (
    <label className="number-field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {format && <small>{format(value)}</small>}
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className="action-button" onClick={onClick} type="button">
      {icon}
      <span>{label}</span>
    </button>
  );
}

function isSimulationResult(value: unknown): value is SimulationResult {
  return Boolean(
    value &&
      typeof value === "object" &&
      "summary" in value &&
      "yearly_results" in value
  );
}

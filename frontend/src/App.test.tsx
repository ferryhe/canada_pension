import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const simulation = {
  yearly_results: [
    {
      year: 2051,
      age: 65,
      phase: "retirement",
      withdrawals: {
        tfsa: 1000,
        rrsp: 0,
        non_registered: 1000,
        investment_loan_repayment: 0,
        spouse_rrsp: 1000
      },
      benefits: { oas: 0, oas_recovery: 0, cpp: 0, gis: 10000 },
      tax: {
        taxable_income: 1000,
        federal_tax: 0,
        ontario_tax: 0,
        ontario_surtax: 0,
        ontario_health_premium: 0,
        oas_recovery: 0,
        total_tax: 0
      },
      after_tax_income: 13000,
      accounts: {
        tfsa: 100000,
        rrsp: 900000,
        non_registered: 120000,
        investment_asset: 400000,
        investment_loan: 0,
        spouse_rrsp: 500000,
        net_worth: 2020000
      },
      warnings: []
    }
  ],
  summary: {
    retirement_year: 2051,
    summary_end_age: 95,
    first_retirement_after_tax_income: 13000,
    average_retirement_after_tax_income: 13000,
    total_after_tax_income: 13000,
    ending_net_worth: 2020000,
    lowest_net_worth: 2020000,
    peak_taxable_income: 1000,
    suggestions: ["Compare scenarios"]
  },
  warnings: [],
  source_version: { policy_year: 2026, province: "ON", benefit_quarter: "2026-Q2", sources: [] }
};

describe("App", () => {
  let reportShouldFail = false;

  beforeEach(() => {
    reportShouldFail = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes("/api/v1/simulate")) {
          return jsonResponse(simulation);
        }
        if (url.includes("/api/v1/compare")) {
          return jsonResponse({
            comparison_table: [
              {
                name: "Base",
                description: "",
                retirement_age: 65,
                cpp_start_age: 71,
                oas_start_age: 71,
                first_retirement_after_tax_income: 13000,
                average_retirement_after_tax_income: 13000,
                ending_net_worth: 2020000,
                warnings: []
              }
            ],
            best_scenario: "Base"
          });
        }
        if (url.includes("/api/v1/chat")) {
          const body = JSON.parse(String(init?.body ?? "{}"));
          const lastMessage = body.messages[body.messages.length - 1]?.content ?? "";
          if (lastMessage.includes("导出PDF")) {
            return jsonResponse({
              message: "好的，我会为当前模拟结果准备 PDF 报告。",
              intent: "report",
              model: "local-fallback",
              applied_config: body.config,
              actions: [{ type: "report", format: "pdf" }],
              missing_fields: [],
              warnings: [],
              calculations: []
            });
          }
          return jsonResponse({
            message: "已完成模拟。",
            intent: "simulate",
            model: "local-fallback",
            applied_config: {
              profile: {
                current_age: 40,
                retirement_age: 65,
                life_expectancy: 95,
                projection_end_age: 100
              },
              accounts: {
                tfsa: { balance: 50000, annual_contribution: 0 },
                rrsp: { balance: 500000, annual_contribution: 33000 },
                non_registered: { balance: 50000, annual_contribution: 0 },
                investment_loan: {
                  gross_asset_balance: 300000,
                  loan_balance: 300000,
                  annual_repayment: 15000,
                  interest_rate: 0.05
                },
                spouse_rrsp: { balance: 300000, annual_contribution: 0 }
              },
              assumptions: { annual_return: 0.08, inflation: 0.03, oas_cpp_growth: 0.025 },
              benefits: {
                oas: { start_age: 71, annual_amount: 8916.6 },
                cpp: { start_age: 71, annual_amount: 16747 },
                gis: { enabled: true, annual_max: 13318.2, income_cutoff: 22512 }
              },
              tax: { province: "ON", capital_gains_inclusion_rate: 0.5 },
              withdrawal_strategy: {
                tfsa_rate: 0.05,
                non_registered_rate: 0.05,
                capital_gain_ratio: 0.5,
                spouse_rrsp_rate: 0.04
              }
            },
            actions: [],
            missing_fields: [],
            warnings: [],
            calculations: [{ tool: "simulate_retirement", output: simulation }]
          });
        }
        if (url.includes("/api/v1/report")) {
          if (reportShouldFail) {
            return new Response(JSON.stringify({ detail: "WeasyPrint missing" }), {
              headers: { "Content-Type": "application/json" },
              status: 503
            });
          }
          return new Response(new Blob(["report"], { type: "application/pdf" }));
        }
        throw new Error(`Unexpected request ${url} ${init?.method}`);
      })
    );
    vi.stubGlobal("open", vi.fn());
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:report"),
      revokeObjectURL: vi.fn()
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders default simulation results", async () => {
    render(<App />);
    expect(await screen.findByText("Canada Retirement Planner")).toBeInTheDocument();
    expect(await screen.findByText("2051")).toBeInTheDocument();
    expect(screen.getAllByText("$13,000").length).toBeGreaterThan(0);
    expect(screen.getByText("Compare scenarios")).toBeInTheDocument();
    expect(screen.getByText(/ON 2026/)).toBeInTheDocument();
  });

  it("runs comparison from the toolbar", async () => {
    render(<App />);
    await screen.findByText("2051");
    await userEvent.click(screen.getAllByRole("button", { name: /对比/i })[0]);
    expect(await screen.findByText(/情景对比/)).toBeInTheDocument();
  });

  it("submits a chat prompt and applies tool output", async () => {
    render(<App />);
    await screen.findAllByText("2051");
    await userEvent.clear(screen.getByPlaceholderText("40岁，RRSP50万，65退休"));
    await userEvent.type(screen.getByPlaceholderText("40岁，RRSP50万，65退休"), "按默认计算");
    await userEvent.click(screen.getByTitle("Send"));
    await waitFor(() => expect(screen.getByText("已完成模拟。")).toBeInTheDocument());
  });

  it("edits parameters and sends the updated config", async () => {
    render(<App />);
    await screen.findByText("2051");
    await userEvent.clear(screen.getByLabelText("预期寿命"));
    await userEvent.type(screen.getByLabelText("预期寿命"), "90");
    await userEvent.click(screen.getByRole("button", { name: /Run/i }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/simulate"),
        expect.objectContaining({ body: expect.stringContaining('"life_expectancy":90') })
      )
    );
  });

  it("shows report export errors from chat actions", async () => {
    reportShouldFail = true;
    render(<App />);
    await screen.findByText("2051");
    await userEvent.clear(screen.getByPlaceholderText("40岁，RRSP50万，65退休"));
    await userEvent.type(screen.getByPlaceholderText("40岁，RRSP50万，65退休"), "导出PDF");
    await userEvent.click(screen.getByTitle("Send"));
    expect(await screen.findByText("WeasyPrint missing")).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200
  });
}

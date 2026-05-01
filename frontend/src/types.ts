export type SimulationConfig = {
  profile: {
    current_age: number;
    retirement_age: number;
    life_expectancy: number;
    projection_end_age: number;
  };
  accounts: {
    tfsa: { balance: number; annual_contribution: number };
    rrsp: { balance: number; annual_contribution: number };
    non_registered: { balance: number; annual_contribution: number };
    investment_loan: { balance: number; annual_repayment: number; interest_rate: number };
    spouse_rrsp: { balance: number; annual_contribution: number };
  };
  assumptions: {
    annual_return: number;
    inflation: number;
    oas_cpp_growth: number;
  };
  benefits: {
    oas: { start_age: number; annual_amount: number };
    cpp: { start_age: number; annual_amount: number };
    gis: { enabled: boolean; annual_max: number; income_cutoff: number };
  };
  tax: {
    province: "ON";
    capital_gains_inclusion_rate: number;
  };
  withdrawal_strategy: {
    tfsa_rate: number;
    non_registered_rate: number;
    capital_gain_ratio: number;
    spouse_rrsp_rate: number;
  };
};

export type YearlyResult = {
  year: number;
  age: number;
  phase: "accumulation" | "retirement";
  withdrawals: {
    tfsa: number;
    rrsp: number;
    non_registered: number;
    investment_loan_repayment: number;
    spouse_rrsp: number;
  };
  benefits: {
    oas: number;
    oas_recovery: number;
    cpp: number;
    gis: number;
  };
  tax: {
    taxable_income: number;
    federal_tax: number;
    ontario_tax: number;
    ontario_surtax: number;
    ontario_health_premium: number;
    oas_recovery: number;
    total_tax: number;
  };
  after_tax_income: number;
  accounts: {
    tfsa: number;
    rrsp: number;
    non_registered: number;
    investment_asset: number;
    investment_loan: number;
    spouse_rrsp: number;
    net_worth: number;
  };
  warnings: string[];
};

export type SimulationResult = {
  yearly_results: YearlyResult[];
  summary: {
    retirement_year: number;
    first_retirement_after_tax_income: number;
    average_retirement_after_tax_income: number;
    total_after_tax_income: number;
    ending_net_worth: number;
    lowest_net_worth: number;
    peak_taxable_income: number;
    suggestions: string[];
  };
  warnings: string[];
  source_version: {
    policy_year: number;
    province: string;
    benefit_quarter: string;
    sources: Array<{ name: string; url: string; effective_date: string }>;
  };
};

export type ScenarioComparison = {
  comparison_table: Array<{
    name: string;
    description: string;
    retirement_age: number;
    cpp_start_age: number;
    oas_start_age: number;
    first_retirement_after_tax_income: number;
    average_retirement_after_tax_income: number;
    ending_net_worth: number;
    warnings: string[];
  }>;
  best_scenario: string;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type ChatResponse = {
  message: string;
  calculations: Array<{ tool: string; output: unknown }>;
  model: string;
};

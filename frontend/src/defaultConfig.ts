import type { SimulationConfig } from "./types";

export const defaultConfig: SimulationConfig = {
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
    investment_loan: { balance: 300000, annual_repayment: 15000, interest_rate: 0.05 },
    spouse_rrsp: { balance: 300000, annual_contribution: 0 }
  },
  assumptions: {
    annual_return: 0.08,
    inflation: 0.03,
    oas_cpp_growth: 0.025
  },
  benefits: {
    oas: { start_age: 71, annual_amount: 8916.6 },
    cpp: { start_age: 71, annual_amount: 16747 },
    gis: { enabled: true, annual_max: 13318.2, income_cutoff: 22512 }
  },
  tax: {
    province: "ON",
    capital_gains_inclusion_rate: 0.5
  },
  withdrawal_strategy: {
    tfsa_rate: 0.05,
    non_registered_rate: 0.05,
    capital_gain_ratio: 0.5,
    spouse_rrsp_rate: 0.04
  }
};

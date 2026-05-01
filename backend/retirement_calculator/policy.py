from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bracket:
    threshold: float
    rate: float


@dataclass(frozen=True)
class PolicySource:
    name: str
    url: str
    effective_date: str


POLICY_YEAR = 2026
PROVINCE = "ON"
BENEFIT_QUARTER = "2026-Q2"

SOURCES = [
    PolicySource(
        "CPP/OAS quarterly report",
        "https://www.canada.ca/en/employment-social-development/programs/pensions/"
        "pension/statistics/2026-quarterly-april-june.html",
        "2026-04",
    ),
    PolicySource(
        "OAS payment amounts",
        "https://www.canada.ca/en/services/benefits/publicpensions/old-age-security/"
        "payments.html",
        "2026-04",
    ),
    PolicySource(
        "CRA T4032-ON 2026",
        "https://www.canada.ca/content/dam/cra-arc/migration/cra-arc/tx/bsnss/"
        "tpcs/pyrll/t4032/2026/t4032-on-1-26e.pdf",
        "2026-01",
    ),
    PolicySource(
        "CRA registered plan limits",
        "https://www.canada.ca/en/revenue-agency/services/tax/registered-plans-"
        "administrators/pspa/mp-rrsp-dpsp-tfsa-limits-ympe.html",
        "2025-12-01",
    ),
    PolicySource(
        "CRA RRIF minimum amount",
        "https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/"
        "completing-slips-summaries/t4rsp-t4rif-information-returns/payments/"
        "minimum-amount-a-rrif.html",
        "2026-01-07",
    ),
]

FEDERAL_BRACKETS = [
    Bracket(0, 0.1400),
    Bracket(58_523.01, 0.2050),
    Bracket(117_045.01, 0.2600),
    Bracket(181_440.01, 0.2900),
    Bracket(258_482.01, 0.3300),
]

ONTARIO_BRACKETS = [
    Bracket(0, 0.0505),
    Bracket(53_891.01, 0.0915),
    Bracket(107_785.01, 0.1116),
    Bracket(150_000.01, 0.1216),
    Bracket(220_000.01, 0.1316),
]

FEDERAL_BASIC_PERSONAL_MAX = 16_452.0
FEDERAL_BASIC_PERSONAL_MIN = 14_829.0
FEDERAL_BPA_PHASEOUT_START = 181_440.0
FEDERAL_BPA_PHASEOUT_END = 258_482.0

ONTARIO_BASIC_PERSONAL_AMOUNT = 12_989.0
ONTARIO_TAX_REDUCTION_BASIC = 300.0
ONTARIO_SURTAX_THRESHOLD_1 = 5_818.0
ONTARIO_SURTAX_THRESHOLD_2 = 7_446.0

CPP_MAX_MONTHLY_65 = 1_507.65
CPP_AVERAGE_MONTHLY_65 = 925.35
CPP_YMPE = 74_600.0
CPP_YAMPE = 85_000.0
CPP_BASE_EXEMPTION = 3_500.0

OAS_MAX_MONTHLY_65_TO_74 = 743.05
OAS_MAX_MONTHLY_75_PLUS = 817.36
GIS_SINGLE_MAX_MONTHLY = 1_109.85
GIS_SINGLE_INCOME_CUTOFF = 22_512.0

OAS_RECOVERY_THRESHOLD_2026 = 95_323.0
OAS_RECOVERY_MAX_65_TO_74 = 154_753.0
OAS_RECOVERY_MAX_75_PLUS = 160_696.0
OAS_RECOVERY_RATE = 0.15

RRSP_DOLLAR_LIMIT = 33_810.0
TFSA_DOLLAR_LIMIT = 7_000.0

CAPITAL_GAINS_INCLUSION_RATE = 0.50

RRIF_FACTORS_71_PLUS = {
    71: 0.0528,
    72: 0.0540,
    73: 0.0553,
    74: 0.0567,
    75: 0.0582,
    76: 0.0598,
    77: 0.0617,
    78: 0.0636,
    79: 0.0658,
    80: 0.0682,
    81: 0.0708,
    82: 0.0738,
    83: 0.0771,
    84: 0.0808,
    85: 0.0851,
    86: 0.0899,
    87: 0.0955,
    88: 0.1021,
    89: 0.1099,
    90: 0.1192,
    91: 0.1306,
    92: 0.1449,
    93: 0.1634,
    94: 0.1879,
    95: 0.20,
}


def source_version() -> dict[str, object]:
    return {
        "policy_year": POLICY_YEAR,
        "province": PROVINCE,
        "benefit_quarter": BENEFIT_QUARTER,
        "sources": [source.__dict__ for source in SOURCES],
    }

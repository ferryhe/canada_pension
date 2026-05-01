# Excel Demonstration Reference

The workbook `retirement planning tool.xlsx` is a demonstration model, not the
canonical calculation engine for this application. The product calculation mode
remains the Ontario/Federal 2026 rules implemented in the backend.

## Workbook Shape

- Sheet: `retirement`
- Range: `A1:V90`
- Main input row: row 4
- Projection table: age 40 through 100

## Key Inputs

| Cell | Label | Demo Value |
| --- | --- | ---: |
| C4 | RRSP contribution | 33,000 |
| D4 | annual yield | 8% |
| E4 | Retire @ | 65 |
| F4 | CPP/OAS @ | 71 |
| G4 | RRSP melt | 200,000 |
| H4 | Inflation | 3% |
| I4 | OAS | 9,000 |
| J4 | CPP | 16,747 |
| K4 | OAS/CPP inf | 2.5% |
| L4 | Spousal RRSP melt | 20,000 |

## Column Map

| Columns | Meaning |
| --- | --- |
| A:B | Year index and age |
| C | Demonstration retirement income |
| D:E | TFSA in/outflow and balance |
| F:G | RRSP in/outflow and balance |
| H:I | Non-registered in/outflow and balance |
| J:K | Investment loan gross asset and net balance |
| L:M | PAR insurance loan and benefit placeholders |
| N:P | Principal OAS, CPP, GIS |
| R:S | Spousal additional flow and investment |
| T:V | Spousal OAS, CPP, GIS placeholders |

## Differences From Official Mode

- The workbook is a cash-flow demonstration and does not implement the full CRA
  2026 tax calculation used by the backend.
- RRSP melt is hard-coded and staged in the workbook; official mode uses RRIF
  minimum withdrawals from age 71.
- TFSA and non-registered withdrawals in the workbook follow the sheet formulas;
  official mode uses configurable withdrawal rates.
- PAR insurance and spousal government benefit columns are reference-only for
  now. The MVP intentionally models only the principal user's OAS/CPP/GIS and
  treats spouse RRSP as simplified household cash flow.

## Future Candidate

A future `demo_excel` mode can reproduce these formulas exactly for sales demos.
That mode should be separate from the official calculation mode so users can see
which results are demonstration cash flow and which are policy-based estimates.

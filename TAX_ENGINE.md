# Portugal 2025 annual net benchmark — Phase 6B

This module provides a **standardized annual benchmark**, not an official personal IRS liquidation and not a payslip calculator.

## Scope

The benchmark is restricted to:

- Portugal, mainland;
- tax year 2025;
- one full-year resident taxpayer;
- single, no dependents, no disability;
- category A employment income only;
- general Social Security regime;
- entire annual gross assumed subject to the employee contribution rate;
- no IRS Jovem, NHR/IFICI or other special regime;
- no other income;
- eligible general-family expenses must be supplied explicitly;
- all other personal collection deductions are set to zero **only by benchmark contract**.

Unsupported years, islands, household structures and special regimes return `unavailable`.

## Classification

A complete calculation returns:

`status: benchmark_estimate`

This status is intentionally distinct from `verified`. It means that the calculation uses verified 2025 statutory components under a reproducible benchmark contract, while not claiming to reproduce the taxpayer's official annual assessment.

If `eligible_household_expenses` is omitted, the result remains `partial` and net income is withheld.

## Calculation

1. Employee Social Security benchmark: annual gross × 11%.
2. Category A specific deduction: article 25 rule, using the annualized contribution amount as the mandatory-contribution benchmark.
3. Minimum existence: historical 2025 article 70 statutory expression.
4. Taxable income: gross − specific deduction − minimum-existence abatement.
5. General collection: article 68(2) statutory arithmetic.
6. Additional solidarity collection: article 68-A.
7. General-family expense credit: article 78-B, 35% of explicit eligible expenses, capped at €250.
8. Other personal credits: €0 only as a benchmark assumption.
9. Benchmark IRS: max(0, general collection + solidarity − explicit credit).
10. Benchmark annual net: gross − annualized employee contribution − benchmark IRS.

All arithmetic uses `Decimal`. Monetary values are rounded only at the presentation boundary with the engine's existing `ROUND_HALF_UP` convention. This is **not** asserted to be the AT's legal internal liquidation-rounding convention.

## Social Security limitation

The 11% employee rate is verified for the restricted general-regime scenario. The benchmark applies it to the annual fully subject gross. It does not claim that this annual product exactly equals the sum of payroll-period contributions after any per-period monetary rounding.

Accordingly, the component is labelled `benchmark_estimate`, not a verified payroll total.

## Five control cases

With €1,000 of eligible article-78-B expenses:

| Annual gross | Benchmark IRS | Annual net | Annual net / 12 |
| ---: | ---: | ---: | ---: |
| €15,000 | €1,153.99 | €12,196.01 | €1,016.33 |
| €25,000 | €3,310.56 | €18,939.44 | €1,578.29 |
| €40,000 | €8,146.61 | €27,453.39 | €2,287.78 |
| €60,000 | €15,471.89 | €37,928.11 | €3,160.68 |
| €100,000 | €31,755.10 | €57,244.90 | €4,770.41 |

The machine-readable cases are in `docs/tax/portugal_2025_benchmark_cases.json`.

## API

- `GET /v1/tax/countries`
- `GET /v1/tax/years/{country}`
- `GET /v1/tax/assumptions/{country}`
- `GET /v1/tax/calculate`

Example:

```text
/v1/tax/calculate?country=PT&annual_gross=25000&tax_year=2025&scenario=single_employee_no_dependents&region=mainland&eligible_household_expenses=1000
```

FastAPI and native WSGI call the same tax engine.

EarnWage overview/comparison may consume the benchmark only when the user explicitly selects the tax scenario and tax year. Net purchasing-power ranking remains unavailable in this phase.

## Evidence

The historical source inventory is stored in `docs/tax/portugal_2025_sources.json`. It preserves the official AT/Diário da República sources and hashes previously audited in PR #13.

This phase deliberately does not alter salary datasets, FX, economic indicators, Android code or deployment.

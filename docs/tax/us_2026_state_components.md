# US 2026 state wage components — continuation

Reviewed 2026-10-04. These components feed the existing EarnWage overview and comparison fiscal context. They do not produce net income and do not extend the country-neutral net tax engine.

## Pennsylvania

Official source: https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax

The current Department of Revenue page confirms a 3.07% income tax rate and no standard deduction or personal exemption. The preview assumes full-year PA residence and all supplied wages are PA-taxable compensation. For USD 100,000, the pre-credit schedule amount is USD 3,070.00.

This is a partial illustration. Tax Forgiveness, Working Pennsylvanians Tax Credit, other credits, employee expenses, deductions and compensation exclusions are not calculated. Local taxes (including Philadelphia), employee unemployment contributions and multistate sourcing remain excluded. Final state wage tax is null, as is net income. Missing gross salary produces no monetary preview.

## Existing components

California source: https://edd.ca.gov/en/Payroll_Taxes/Rates_and_Withholding

The 2026 SDI employee rate is 1.3%, without a wage ceiling. This is a contribution, not state income tax. All wages are assumed SDI-covered; exemptions and voluntary plans remain excluded.

New York source: https://www.nysenate.gov/legislation/laws/TAX/601

Section 601(c)(1)(B)(vii) supplies the existing 2026 single-resident statutory schedule. Its rounded statutory base amounts are preserved; this change does not reconstruct bases using continuous marginal arithmetic. The existing USD 8,000 deduction assumption is unchanged. Preview stops above USD 107,650 gross in the wage-only AGI scenario, where supplemental recapture needs implementation. Credits, NYC and Yonkers remain excluded.

## Arithmetic and validation

State calculations now use Decimal and ROUND_HALF_UP, matching the federal component module, with rounding at the output boundary. Legacy JSON numbers and field names are retained. Supplied amounts are validated as finite, positive and no greater than USD 100 million, including zero-tax states. Unsupported years retain unavailable status.

Regression cases cover half-cent rounding, invalid amounts, New York schedule and recapture boundaries, Pennsylvania configuration, and fiscal-context integration without net income.

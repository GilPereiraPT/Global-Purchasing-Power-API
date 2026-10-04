# Explicit ordinary-wage federal model, 2026

The API now accepts `single_ordinary_wages_federal_benchmark` for the first TX/FL workstream. It returns an explicitly scoped federal component estimate, **not complete US net income**. The existing scenario stays unchanged. Neither `net_income` nor final state/local deductions are activated. There is no DB import or production write.

## Scope and required facts

All required facts are exposed by `/v1/tax/assumptions/US` in the scenario metadata. The model requires age 25–64, no blindness/dependency, a valid SSN eligibility declaration (never the SSN itself), and federal/Social Security/Medicare wages explicitly equal to gross. It requires explicit zero qualified tips, overtime and nonitemizer charitable contributions. `ordinary_wage_model_confirmed=true` affirms the full listed model assumptions: ordinary employee wages only, full-year resident, single without dependents, no other income, deductions, credits, prior-year credits, AMT preferences or special taxes. This declaration does not independently prove a person's eligibility.

Missing is not zero or consent. Special deductions, distinct wage bases, unsupported facts, ages, years or states do not produce the model. Gross is restricted to 19540–500000. Below the range, childless EITC eligibility/refunds need a separate model; above it, AMT phaseout needs implementation. Unsupported cases remain partial with specific reasons.

## Arithmetic and sources

The regular schedule and 16100 basic deduction use IRS Rev. Proc. 2025-32, section **4.01 Table 3** and 4.14. Childless EITC is zero only within this wage-only single scenario at or above the published 19540 completed phaseout (4.06). Age/blindness/dependent and senior relief are excluded by explicit facts, rather than silently omitted. Qualified tips/overtime, car-loan interest, educator expenses, charitable contributions and all other deduction/credit circumstances are excluded by the confirmed model; positive tips/overtime/charity reject the model.

AMTI restores the standard deduction to wage-only income. It uses the actual 2026 exemption 90100 and rate breakpoint 244500 from section 4.10, with structural ordinary rates 26%/28% and the standard-deduction addback described in Form 6251 instructions. Those instructions are currently **2025**: they are cited only for structural computation, never for their 2025 thresholds. The range stops at the 2026 500000 phaseout start, so neither the obsolete 25% phaseout nor the new 50% phaseout is extrapolated. Additional AMT is max(0, tentative minimum tax minus regular tax), not automatically zero.

FICA and single Additional Medicare use the recovered IRS evidence from #40. Annual cents are calculated at the output boundary; they do not reproduce every pay-period rounding operation, withholding, final tax-table return, payment/refund or voluntary deduction. IRS Publication 505 (2026) supplies the annual projected tax computation context; draft 2026 ATS scenarios are not treated as final reference returns.

New source snapshots include Texas's constitutional income-tax prohibition, FL 2026 natural-person income-tax exclusion and employer reemployment contribution non-deduction rule. These support continuing jurisdiction work but are **not** taken as evidence that every local levy, employee premium or special occupation is covered. TWC's direct response was 403. State/local/premium amounts therefore remain null; no zero is used to activate total take-home pay.

## Output

The named component `income_after_federal_components_before_state_local_and_other_deductions` is a mathematical balance after the modeled federal income tax and employee FICA/Additional Medicare. It is deliberately a component; it is not placed in the central `net_income` field or advertised as benchmark take-home pay. For the confirmed 100000 wage model, federal schedule tax is 13170, employee federal contributions are 7650, and this federal-only balance is 79180. These are model checks, not independently assessed personal tax returns.

## Remaining work

TX/FL: finish source-backed local/premium applicability and independent complete reference cases before promoting a result. Federal: extend eligibility, refundable EITC, special deductions, high-income AMT and final annual rounding. NY/CA/PA: complete their specific annual/local/credit and mandatory contribution rules. Do not route source archives or tax rules into salary publication packages.

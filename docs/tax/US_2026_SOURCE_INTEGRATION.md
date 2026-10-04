# US 2026 source integration

This branch consolidates PRs #30–33 and the reference document from #37 on current main. The federal adapter remains partial, and the state modules remain offline components. None produces net income or becomes a benchmark. No database, salary package, Android or deployment change is included.

## Evidence recovered on 2026-10-04

Six official HTML responses were downloaded successfully: IRS Rev. Proc. 2025-32 in IRB 2025-45, IRS Topics 751 and 560, IRS Publication 15 (2026), California EDD rates and Pennsylvania Revenue PIT. Exact response hashes, sizes, original URLs, acquisition times and scoped review metadata are in `data/us_tax_2026_source_evidence.json`. Raw responses and the acquisition manifest are preserved in the separately delivered `earnwage-us-fiscal-sources-20261004.zip`, outside Git. Checksums identify the response bytes; they do not prove completeness or legal applicability by themselves.

The SSA page timed out. IRS Publication 15 (2026) explicitly corroborates the 184500 wage limit and 6.2% employee rate, so federal runtime evidence points to that successfully acquired source. NY Senate returned HTTP 403. Its earlier browser-reviewed reference in #37 remains useful, but no raw NY response is claimed or promoted to reviewed runtime evidence.

Reviewed parameters: 2026 single regular marginal brackets and basic deduction 16100; employee Social Security 6.2% up to 184500; employee Medicare 1.45% without a ceiling; single wage-only Additional Medicare 0.9% above 200000; ordinary California SDI 1.3% with no ceiling; current PA PIT 3.07% and no standard deduction/personal exemption. PA's current page is a rate reference reviewed on the date, not a validated complete 2026 annual instruction set.

## Runtime meaning

`parameters_reviewed` records a limited source review, deliberately distinct from `verified`. The central engine rejects it as sufficient evidence for a complete verified/benchmark outcome. Federal numerical values and existing component names stay compatible; component status now says `reviewed_parameters_assumed_facts`. California and Pennsylvania use the same limited status for their existing arithmetic. Unknown state rules remain blocked; NY acquisition shows the actual 403 instead of repeating the old ProxyError.

Federal amounts still assume full covered ordinary wages when explicit wage bases are absent. Basic deduction arithmetic does not apply age/blindness/dependent adjustments, senior deductions, tips/overtime relief, EITC or AMT. Output cents are presentation rounding, not a validated tax-table assessment or sum of payroll withholding. No missing credit or local contribution becomes zero.

## Remaining work before a usable net calculation

1. Complete federal eligibility/deductions/credits, AMT and legal annual rounding for the explicitly selected household and wage coverage; obtain independent final-assessment cases.
2. Validate TX/FL state/local applicability and mandatory employee premiums before activating their federal-plus-state result.
3. Obtain NY annual deduction/credit/recapture/locality and DBL/PFL evidence; implement the full applicable schedule.
4. Obtain CA annual FTB schedules/credits/adjustments/high-income component and SDI coverage evidence. EDD withholding tables are not substituted for annual FTB liability.
5. Complete PA taxable compensation/exclusions, Tax Forgiveness/WPTC, unemployment and residence/work local taxes.

Fiscal rules presently reside in code. This archive and the source review JSON are evidence, not uploadable salary or fiscal database packages. Integrating code alone does not update a fiscal database or authorize publication.

## Validation

Existing federal/state arithmetic, fact validation, ASGI/WSGI parity and unavailable-net tests are retained. New tests check all six IRS published accumulated tax anchors independently of marginal integration, scoped source statuses, CA/PA unknown components, NY 403, unknown-source rejection and audit metadata isolation. The complete suite is run before opening the integration PR.

"""2026 US state wage-income-tax scope. No personal net-pay inference.

This module covers ONLY state personal income tax on ordinary employee wages.
It does not model other payroll deductions, local taxes, nonwage income or
multistate sourcing. A zero state wage-income-tax component is not zero taxes.
"""
NO_STATE_WAGE_INCOME_TAX = frozenset({
    "AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY",
})
SOURCES = [
    "https://taxfoundation.org/data/all/state/state-income-tax-rates-2026/",
    "https://www.revenue.nh.gov/news-and-media/repeal-nh-interest-and-dividends-tax-now-effect",
    "https://dor.wa.gov/taxes-rates/income-tax/frequently-asked-questions-about-income-tax",
]

def state_wage_income_tax(region, tax_year=2026, annual_gross=None):
    """Return scoped tax on W-2 wages, never a claim of total state taxes."""
    if not region:
        return {"status": "region_needed", "state_wage_income_tax": None,
                "reason": "Select a state to determine the state wage-income-tax component."}
    if tax_year != 2026:
        return {"status": "unavailable", "state": region, "tax_year": tax_year,
                "state_wage_income_tax": None,
                "reason": "Only tax year 2026 is reviewed for state wage-income-tax status."}
    if region in NO_STATE_WAGE_INCOME_TAX:
        return {"status": "available", "state": region, "tax_year": tax_year,
                "currency": "USD", "state_wage_income_tax": 0.0,
                "scope": "state personal income tax on ordinary employee wages only",
                "not_included": ["Federal income tax", "FICA", "Local taxes",
                                 "Other state payroll deductions or premiums",
                                 "Capital gains and nonwage income",
                                 "Multistate residence and work sourcing"],
                "sources": SOURCES,
                "note": "Zero state wage-income tax does NOT mean zero state taxes or complete take-home pay."}
    if region == "CA":
        # California EDD 2026: employee SDI 1.3%, no taxable wage ceiling.
        # This is a payroll contribution, NOT state personal income tax.
        sdi = round(annual_gross * 0.013, 2) if annual_gross is not None else None
        return {"status": "partial_components", "state": "CA", "tax_year": 2026,
                "state_wage_income_tax": None,
                "employee_state_disability_insurance": sdi,
                "sdi_rate": 0.013,
                "sdi_assumption": "All supplied wages are subject to California SDI; excludes exempt workers and approved voluntary plans.",
                "sdi_source": "https://edd.ca.gov/en/Payroll_Taxes/Rates_and_Withholding",
                "state_income_tax_status": "not_implemented",
                "reason": "California state income-tax liability, credits and deductions are not yet validated; SDI is a separate payroll contribution."}
    if region == "NY":
        taxable = max(0.0, annual_gross - 8000) if annual_gross is not None else None
        # NY Tax Law 601(c)(1)(B)(vii): 2026 SINGLE schedule only.
        # For this wage-only scenario AGI < 107,650: no supplemental recapture.
        brackets = ((8500, 0, .039), (11700, 332, .044),
                    (13900, 473, .0515), (80650, 586, .054),
                    (215400, 4191, .059))
        preview = None
        if taxable is not None and annual_gross <= 107650:
            for ceiling, base, rate in brackets:
                if taxable <= ceiling:
                    floor = (0 if ceiling == 8500 else
                             8500 if ceiling == 11700 else
                             11700 if ceiling == 13900 else
                             13900 if ceiling == 80650 else 80650)
                    preview = round(base + (taxable - floor) * rate, 2)
                    break
        return {"status": "partial_components" if preview is not None else "not_implemented", "state": "NY", "tax_year": 2026,
                "state_wage_income_tax": None,
                "standard_deduction_single_reference": 8000,
                "state_taxable_income_preview": taxable,
                "state_income_tax_schedule_before_credits": preview,
                "schedule_scope": "2026 NY Tax Law 601(c) single resident, wage-only scenario, AGI <= 107650; no NY City or Yonkers tax, no credits",
                "schedule_source": "https://www.nysenate.gov/legislation/laws/TAX/601",
                "standard_deduction_source": "https://www.tax.state.ny.us/forms/current-forms/it/it2104i.htm",
                "reason": "Pre-credit NY statutory schedule is a partial illustration; state tax after credits and city/local taxes are not validated."}
    return {"status": "not_implemented", "state": region, "tax_year": tax_year,
            "state_wage_income_tax": None,
            "reason": "State-specific wage-income-tax calculation has not been validated."}

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

def state_wage_income_tax(region, tax_year=2026):
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
    return {"status": "not_implemented", "state": region, "tax_year": tax_year,
            "state_wage_income_tax": None,
            "reason": "State-specific wage-income-tax calculation has not been validated."}

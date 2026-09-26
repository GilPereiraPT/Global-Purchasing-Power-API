"""2026 LIMITED tax-component illustrations, never a net-pay calculator.

Inputs are a hypothetical annual wage for a standard employee. Applicable 2026
rules are intentionally separate from source wage observations dated 2021/2025.
Local income tax, credits, pension/health deductions and actual withholding are
not inferred. Decimal arithmetic prevents floating-point currency drift.
"""
from decimal import Decimal, ROUND_HALF_UP

IRS_2026 = "https://www.irs.gov/irb/2025-45_IRB"
IRS_FICA = "https://www.irs.gov/taxtopics/tc751"
IRS_ADDITIONAL_MEDICARE = "https://www.irs.gov/taxtopics/tc560"
CRA_2026 = ("https://www.canada.ca/en/revenue-agency/services/forms-publications/"
            "payroll/t4032-payroll-deductions-tables/t4032oc-jan/"
            "t4032oc-january-general-information.html")
US_SINGLE_BRACKETS = (
    ("12400", "0.10"), ("50400", "0.12"), ("105700", "0.22"),
    ("201775", "0.24"), ("256225", "0.32"), ("640600", "0.35"),
    (None, "0.37"),
)
PROVINCES_EXCEPT_QUEBEC = {
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU",
    "ON", "PE", "SK", "YT",
}


def amount(value):
    v = Decimal(str(value))
    if not v.is_finite() or v <= 0 or v > Decimal("100000000"):
        raise ValueError("Annual gross must be greater than zero and no more than 100 million")
    return v


def money(value):
    return float(value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


def marginal(taxable, brackets):
    previous = Decimal(0)
    total = Decimal(0)
    for cap, rate in brackets:
        upper = taxable if cap is None else min(taxable, Decimal(cap))
        if upper > previous:
            total += (upper - previous) * Decimal(rate)
        if cap is None or taxable <= Decimal(cap):
            return total
        previous = Decimal(cap)
    raise ValueError("Invalid marginal brackets")


def components(country, annual_gross, tax_year=2026, filing_status="single", province=None):
    if tax_year != 2026:
        raise ValueError("Only explicitly checked tax year 2026 is supported")
    gross = amount(annual_gross)
    if country == "US":
        if filing_status != "single" or province is not None:
            raise ValueError("US model only supports single filer without province parameter")
        taxable = max(Decimal(0), gross - Decimal("16100"))
        federal = marginal(taxable, US_SINGLE_BRACKETS)
        social_security = min(gross, Decimal("184500")) * Decimal("0.062")
        medicare = gross * Decimal("0.0145")
        additional = max(Decimal(0), gross - Decimal("200000")) * Decimal("0.009")
        return {
            "status": "partial_estimate", "country": "US", "currency": "USD",
            "tax_year": tax_year, "model": "standard single US employee, federal-only",
            "annual_gross": money(gross),
            "assumptions": ["Single filing status", "Standard deduction only",
                            "All wages treated as regular US FICA-covered wages",
                            "No other taxable income or deductions"],
            "components": {
                "federal_income_tax_before_credits": money(federal),
                "employee_social_security": money(social_security),
                "employee_medicare": money(medicare),
                "employee_additional_medicare": money(additional),
            },
            "standard_deduction": 16100,
            "taxable_income_before_credits": money(taxable),
            "net_income": None,
            "net_income_status": "unavailable",
            "not_included": [
                "State or local income taxes", "Credits, additional deductions, AMT",
                "Healthcare premiums, retirement contributions, non-wage income",
                "Real pay-period withholding and individual tax circumstances"
            ],
            "sources": [IRS_2026, IRS_FICA, IRS_ADDITIONAL_MEDICARE],
            "note": "Partial federal illustration for 2026; NOT an estimate of take-home pay.",
        }
    if country == "CA":
        if province not in PROVINCES_EXCEPT_QUEBEC or filing_status != "single":
            raise ValueError("Canada model requires supported province (not QC) and single employee")
        cpp_base = min(max(Decimal(0), gross - Decimal("3500")),
                       Decimal("71100")) * Decimal("0.0495")
        cpp_first = min(max(Decimal(0), gross - Decimal("3500")),
                        Decimal("71100")) * Decimal("0.01")
        cpp_second = min(max(Decimal(0), gross - Decimal("74600")),
                         Decimal("10400")) * Decimal("0.04")
        ei = min(gross, Decimal("68900")) * Decimal("0.0163")
        return {
            "status": "partial_estimate", "country": "CA", "currency": "CAD",
            "tax_year": tax_year, "province": province,
            "model": "2026 standard employee CPP and EI outside Quebec only",
            "annual_gross": money(gross),
            "assumptions": ["Employee aged 18–65, CPP pensionable employment",
                            "EI insurable employment",
                            "One employer and no special contribution exemptions"],
            "components": {
                "employee_cpp_base": money(cpp_base),
                "employee_cpp_first_additional": money(cpp_first),
                "employee_cpp_second_additional": money(cpp_second),
                "employee_employment_insurance": money(ei),
            },
            "federal_income_tax": None,
            "provincial_income_tax": None,
            "net_income": None,
            "net_income_status": "unavailable",
            "not_included": [
                "Federal and provincial income tax",
                "Credits and additional deductions",
                "Employer contributions, actual payroll withholding",
                "Quebec pension and parental insurance regimes",
            ],
            "sources": [CRA_2026],
            "note": "2026 CPP/EI illustration only; NOT an estimate of take-home pay.",
        }
    return {
        "status": "unavailable", "country": country, "tax_year": tax_year,
        "reason": "No validated tax-component model implemented for this country",
        "net_income": None,
    }

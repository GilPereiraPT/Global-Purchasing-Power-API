"""EarnWage client configuration: product branding and progressive region disclosure.

Product name belongs to the Android/web client; backend repository/module and
/v1 contracts remain stable. This is UI metadata, NOT tax-law determination.
"""
from app.catalog import COUNTRY_MAP, SUPPORTED_LANGUAGES

PRODUCT = {
    "name": "EarnWage",
    "subtitle": "Salary & Cost of Living",
    "tagline": "Your salary. Your world.",
    "supported_languages": list(SUPPORTED_LANGUAGES),
    "default_language": "en",
    "language_fallback": "en",
    "portuguese_language": "pt",
}
REGIONS = {
    "US": {
        "kind": "state",
        "label": {"en": "State", "pt": "Estado"},
        "note": {
            "en": "Income taxes and other deductions may vary by state and locality. Without a validated state-level model, results are partial and are not take-home pay.",
            "pt": "Os impostos sobre o rendimento e outras deduções podem variar por estado e localidade. Sem um modelo estadual validado, o resultado é parcial e não representa salário líquido.",
        },
        "options": [
            ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"),
            ("AR", "Arkansas"), ("CA", "California"), ("CO", "Colorado"),
            ("CT", "Connecticut"), ("DE", "Delaware"), ("FL", "Florida"),
            ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
            ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"),
            ("KS", "Kansas"), ("KY", "Kentucky"), ("LA", "Louisiana"),
            ("ME", "Maine"), ("MD", "Maryland"), ("MA", "Massachusetts"),
            ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
            ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"),
            ("NV", "Nevada"), ("NH", "New Hampshire"), ("NJ", "New Jersey"),
            ("NM", "New Mexico"), ("NY", "New York"), ("NC", "North Carolina"),
            ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
            ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"),
            ("SC", "South Carolina"), ("SD", "South Dakota"),
            ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
            ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"),
            ("WV", "West Virginia"), ("WI", "Wisconsin"), ("WY", "Wyoming"),
        ],
    },
    "CA": {
        "kind": "province_or_territory",
        "label": {"en": "Province or territory", "pt": "Província ou território"},
        "note": {
            "en": "Income tax varies by province/territory. Québec has distinct payroll contributions. A selected region alone does not make a partial estimate a net salary.",
            "pt": "O imposto sobre o rendimento varia por província ou território. O Québec tem contribuições salariais próprias. Selecionar a região não transforma um cálculo parcial em salário líquido.",
        },
        "options": [
            ("AB", "Alberta"), ("BC", "British Columbia"),
            ("MB", "Manitoba"), ("NB", "New Brunswick"),
            ("NL", "Newfoundland and Labrador"),
            ("NS", "Nova Scotia"), ("NT", "Northwest Territories"),
            ("NU", "Nunavut"), ("ON", "Ontario"),
            ("PE", "Prince Edward Island"), ("QC", "Québec"),
            ("SK", "Saskatchewan"), ("YT", "Yukon"),
        ],
    },
}


def configuration():
    return {
        "product": PRODUCT,
        "supported_country_codes": list(COUNTRY_MAP),
        "country_count": len(COUNTRY_MAP),
        "occupation_count": 40,
        "country_selector": {"always_visible": True},
        "region_selector": {
            "visibility": "conditional",
            "required_for_initial_comparison": False,
            "supported_countries": list(REGIONS),
            "note": "Region selection affects context, not the availability or completeness of a tax engine.",
        },
        "calculation_policy": {
            "net_salary": "Only display when a validated complete model exists for the user context",
            "partial_estimate": "Identify exclusions explicitly; do not label it net salary",
            "unavailable": "No imputation from another country or region",
        },
        "note": "A UI specification, not a claim that every stated language is translated or every region has tax coverage.",
    }


def region_configuration(country, region=None, tax_year=2026):
    country = country.upper()
    if country not in COUNTRY_MAP:
        return None
    if country not in REGIONS:
        return {"country": country, "visible": False, "region_type": None,
                "options": [], "status": "not_required_for_current_ui"}
    data = REGIONS[country]
    state_status = None
    if country == "US" and region:
        from app.us_state_tax import state_wage_income_tax
        state_status = state_wage_income_tax(region, tax_year)["status"]
    coverage = ("wage_income_tax_only" if state_status == "available" else
                "partial_components" if state_status == "partial_components" else
                "not_implemented")
    return {
        "country": country, "visible": True, "required_for_initial_comparison": False,
        "region_type": data["kind"], "label": data["label"], "note": data["note"],
        "options": [{"code": code, "name": name} for code, name in data["options"]],
        "tax_region_model_status": coverage,
        "warning": "State components are incomplete; this is not take-home pay.",
    }

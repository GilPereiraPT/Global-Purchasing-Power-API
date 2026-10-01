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
    "BR": {
        "kind": "federal_unit",
        "label": {"en": "State or Federal District", "pt": "Estado ou Distrito Federal"},
        "note": {
            "en": "Optional RAIS-derived 2025 occupation-specific state medians for formal 40–44-hour employment. Not state taxes or take-home pay; missing state medians remain unavailable.",
            "pt": "Medianas estaduais RAIS 2025 por profissão, apenas vínculos formais de 40–44 horas. Não são salários líquidos nem impostos estaduais. Dados estaduais em falta não são estimados.",
        },
        "options": [
            ("AC", "Acre"),
            ("AL", "Alagoas"),
            ("AP", "Amapá"),
            ("AM", "Amazonas"),
            ("BA", "Bahia"),
            ("CE", "Ceará"),
            ("DF", "Distrito Federal"),
            ("ES", "Espírito Santo"),
            ("GO", "Goiás"),
            ("MA", "Maranhão"),
            ("MT", "Mato Grosso"),
            ("MS", "Mato Grosso do Sul"),
            ("MG", "Minas Gerais"),
            ("PA", "Pará"),
            ("PB", "Paraíba"),
            ("PR", "Paraná"),
            ("PE", "Pernambuco"),
            ("PI", "Piauí"),
            ("RJ", "Rio de Janeiro"),
            ("RN", "Rio Grande do Norte"),
            ("RS", "Rio Grande do Sul"),
            ("RO", "Rondônia"),
            ("RR", "Roraima"),
            ("SC", "Santa Catarina"),
            ("SP", "São Paulo"),
            ("SE", "Sergipe"),
            ("TO", "Tocantins"),
        ],
    },
    "IN": {
        "kind": "state_or_union_territory",
        "label": {"en": "State or union territory", "pt": "Estado ou território da União"},
        "note": {
            "en": "State selection changes only the published PLFS 2025 NCO occupational-group context. Results are broad survey averages, not a job-specific wage or a state tax calculation. Only regions with released observations are listed.",
            "pt": "A seleção do Estado altera apenas o contexto salarial do grupo NCO do PLFS 2025. São médias de grupos profissionais, não salários da profissão nem cálculos fiscais estaduais. Só são listadas regiões com observações divulgadas.",
        },
        "options": [
            ("28", "Andhra Pradesh"),
            ("12", "Arunachal Pradesh"),
            ("18", "Assam"),
            ("10", "Bihar"),
            ("4", "Chandigarh"),
            ("22", "Chhattisgarh"),
            ("25", "D & N Haveli and Daman & Diu"),
            ("7", "Delhi"),
            ("24", "Gujarat"),
            ("6", "Haryana"),
            ("2", "Himachal Pradesh"),
            ("1", "Jammu & Kashmir"),
            ("20", "Jharkhand"),
            ("29", "Karnataka"),
            ("32", "Kerala"),
            ("37", "Ladakh"),
            ("23", "Madhya Pradesh"),
            ("27", "Maharashtra"),
            ("14", "Manipur"),
            ("17", "Meghalaya"),
            ("15", "Mizoram"),
            ("13", "Nagaland"),
            ("21", "Odisha"),
            ("34", "Puducherry"),
            ("3", "Punjab"),
            ("8", "Rajasthan"),
            ("11", "Sikkim"),
            ("33", "Tamil Nadu"),
            ("36", "Telangana"),
            ("16", "Tripura"),
            ("9", "Uttar Pradesh"),
            ("5", "Uttarakhand"),
            ("19", "West Bengal"),
        ],
    },
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


def region_configuration(country, region=None, tax_year=2026, annual_gross=None):
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
        state_status = state_wage_income_tax(region, tax_year, annual_gross)["status"]
    coverage = ("wage_income_tax_only" if state_status == "available" else
                "partial_components" if state_status == "partial_components" or
                (country == "US" and region == "NY" and tax_year == 2026) else
                "not_implemented")
    return {
        "country": country, "visible": True, "required_for_initial_comparison": False,
        "region_type": data["kind"], "label": data["label"], "note": data["note"],
        "options": [{"code": code, "name": name} for code, name in data["options"]],
        "tax_region_model_status": coverage,
        "warning": ("Indian PLFS regional wages are occupational-group estimates, not exact job wages or net pay." if country == "IN" else "State components are incomplete; this is not take-home pay."),
    }

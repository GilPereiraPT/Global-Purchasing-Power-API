"""EarnWage screen-ready read-only queries; never infer net pay or comparable PPP.

These queries use committed observations and explicitly requested tax scenarios.
They do not trigger Remotive, Eurostat or ECB traffic on every screen render.
"""
from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app import north_america as na
from app.ilostat_import import salary as ilostat_salary, availability as ilostat_availability
from app.ilostat_groups import group_salary
from app.client_config import region_configuration
from app.tax_components import components as tax_components

JOBS = {job["id"]: job for job in OCCUPATIONS}


def region_check(country, region):
    if not region:
        return None
    data = region_configuration(country)
    options = {r["code"] for r in data["options"]}
    if region not in options:
        raise ValueError("Region is not listed for the selected country")
    return region


def wage_for(country, occupation):
    return na.wages(country, occupation) if country in ("US", "CA") else ilostat_salary(country, occupation)


def fiscal_context(country, region, annual_gross, tax_year):
    if annual_gross is None:
        return {"status": "not_requested", "net_income": None,
                "reason": "Supply your own annual gross salary to request a separate fiscal scenario"}
    if country == "CA" and region is None:
        return {"status": "region_needed", "net_income": None,
                "reason": "Select a Canadian province/territory for a partial CPP/EI scenario; income tax is not implemented"}
    if country == "CA" and region == "QC":
        return {"status": "unavailable", "net_income": None,
                "reason": "Quebec QPP, QPIP and EI require a distinct validated tax model"}
    if country in ("US", "CA"):
        return tax_components(country, annual_gross, tax_year=tax_year,
                              province=region if country == "CA" else None)
    return tax_components(country, annual_gross, tax_year=tax_year)


def overview(country, occupation, region=None, annual_gross=None, tax_year=2026):
    """One place/one profession: wages, optional region and independent tax scenario."""
    code = country.upper()
    region = region.upper() if region else None
    if code not in COUNTRY_MAP:
        raise LookupError("Unknown country")
    if occupation not in JOBS:
        raise ValueError("Unknown occupation")
    region_check(code, region)
    selected = COUNTRY_MAP[code]
    wage = wage_for(code, occupation)
    isco = JOBS[occupation]["isco08"]
    major_group = str(isco)[0] if isco and str(isco)[0] in "123456789" else None
    group_context = (group_salary(code, major_group) if major_group else {
        "status": "unavailable", "precision": "isco08_major_group",
        "reason": "No validated ISCO-08 major-group mapping"})
    warnings = []
    if code == "US":
        warnings.append("Federal components only; state and local tax models are not implemented.")
    elif code == "CA":
        warnings.append("Federal/provincial income tax models are not implemented; Quebec payroll differs.")
    if wage.get("status") == "available":
        warnings.append("National occupational observation; it is not a capital-city salary or a job offer.")
        warnings.append("The wage source reference period is distinct from any 2026 tax scenario.")
    else:
        warnings.append("No matching verified occupational observation; no wage has been inferred.")
    warnings.append("ILOSTAT major-group earnings are broad occupational context, not the selected profession's salary or a substitute for missing exact wages.")
    warnings.append("Cost-of-living basket and net purchasing-power comparison are not yet available.")
    return {
        "country": {"code": code, "name": selected["name"],
                    "capital": selected["capital"], "currency": selected["currency"]},
        "occupation": {"id": occupation, "label": JOBS[occupation]["translations"]["en"],
                       "translations": JOBS[occupation]["translations"],
                       "isco08": JOBS[occupation]["isco08"]},
        "region": {"selected": region, "ui": region_configuration(code),
                   "regional_tax_model_status": "not_implemented" if code in ("US","CA") else "not_applicable"},
        "national_occupation_wage": wage,
        "national_major_group_context": group_context,
        "tax_scenario": fiscal_context(code, region, annual_gross, tax_year),
        "capital_cost_of_living": {"status": "unavailable", "value": None},
        "net_purchasing_power": {"status": "unavailable", "value": None},
        "currency_conversion": {"status": "not_requested",
                                "reason": "Use separate live /v1/exchange-rates/{currency}; no inferred FX"},
        "warnings": warnings,
    }


def compare(country_a, country_b, occupation, region_a=None, region_b=None,
            annual_gross_a=None, annual_gross_b=None, tax_year=2026):
    """No overall winner/ranking: side-by-side sourced records with original units."""
    a = overview(country_a, occupation, region_a, annual_gross_a, tax_year)
    b = overview(country_b, occupation, region_b, annual_gross_b, tax_year)
    return {
        "occupation": occupation, "country_a": a, "country_b": b,
        "wage_comparability": {
            "status": "not_normalized",
            "reason": "Units, statistical measures, reference years, NOC/SOC/ISCO scopes and currencies can differ",
        },
        "net_purchasing_power": {"status": "unavailable", "value": None,
            "reason": "Full region-aware income tax and verified living-cost baskets are pending"},
        "display_policy": "Do not rank countries or subtract unvalidated deductions from source wages.",
    }


def coverage():
    """A compact derived summary of real observations, not fictitious coverage."""
    observed = {(c["country"], c["occupation"]): c["latest_period"]
                for c in ilostat_availability()["cells"] if c["status"] == "available"}
    observed.update(na.observed_coverage())
    return {
        "countries": len(COUNTRY_MAP), "occupations": len(OCCUPATIONS),
        "possible_pairs": len(COUNTRY_MAP) * len(OCCUPATIONS),
        "observed_pairs": len(observed),
        "by_country": [
            {"code": code, "observed_occupations": sum(c == code for c, _ in observed),
             "possible_occupations": len(OCCUPATIONS),
             "status": "partial" if any(c == code for c, _ in observed) else "unavailable"}
            for code in COUNTRY_MAP
        ],
        "note": "Counts only actually imported occupation-country observations; never market-wide coverage.",
    }

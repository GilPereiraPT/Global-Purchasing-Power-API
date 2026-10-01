"""EarnWage screen-ready read-only queries; never infer net pay or comparable PPP.

These queries use committed observations and explicitly requested tax scenarios.
They do not trigger Remotive, Eurostat or ECB traffic on every screen render.
"""
from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app import north_america as na
from app import in_plfs
from app import in_nco_crosswalk
from app import br_rais_states
from app import de_entgeltatlas_states
from app import ca_province_wages as ca_province
from app import pt_occupation_wages as pt_wages
from app import uk_ashe_wages as uk_wages
from app import de_entgeltatlas_wages as de_wages
from app import fr_insee_wages as fr_wages
from app import nl_cbs_wages as nl_wages
from app import ch_bfs_wages as ch_wages
from app import it_istat_wages as it_wages
from app import ie_public_wages as ie_wages
from app import ie_cso_groups as ie_groups
from app import ca_statcan_groups as ca_groups
from app import br_cbo
from app import br_rais_wages
from app import br_public_wages
from app import pt_public_wages
from app.ilostat_import import salary as ilostat_salary, availability as ilostat_availability
from app.ilostat_groups import group_salary, group_history
from app.earnwage_history import exact_history
from app.client_config import region_configuration
from app.tax_components import components as tax_components
from app.us_state_tax import state_wage_income_tax

JOBS = {job["id"]: job for job in OCCUPATIONS}



def annual_presentation(wage, group_context):
    """Source-preserving annual display. Never guess contractual 13th/14th payments."""
    if wage.get("status") == "available":
        observations = wage.get("observations")
        if observations:
            requested_measure = wage.get("preferred_measure")
            preferred = (next((o for o in observations
                               if o.get("measure") == requested_measure
                               and o.get("unit", "").endswith("/year")), None)
                         if requested_measure else None)
            if preferred is None:
                preferred = next((o for o in observations if o.get("measure") == "mean"
                                  and o.get("unit", "").endswith("/year")), None)
            if preferred is None:
                preferred = next((o for o in observations if o.get("unit", "").endswith("/year")), None)
            if preferred is not None:
                return {"status":"available", "value":preferred["value"],
                        "currency":preferred["currency"], "unit":"per_year",
                        "kind":"reported_annual", "reference_period":preferred["reference_period"],
                        "source":preferred["source"], "monthly_optional":preferred["value"]/12,
                        "monthly_kind":"annual_divided_by_12",
                        "payments_per_year":None, "payments_verified":False,
                        "note":"Published annual wage; monthly figure is annual/12, not contractual monthly pay."}
        if wage.get("unit", "").startswith("monthly"):
            return {"status":"available", "value":wage["value"]*12,
                    "currency":wage["currency"], "unit":"per_year",
                    "kind":"annualized_12_month_equivalent",
                    "reference_period":wage["period"], "source":wage["source"],
                    "monthly_optional":wage["value"], "monthly_kind":"reported_monthly",
                    "payments_per_year":None, "payments_verified":False,
                    "note":"Monthly earnings × 12 for comparison only. This is not verified total annual remuneration; extra payments are not assumed."}
        if (wage.get("source_unit", "").endswith("/hour") or
                "hourly" in wage.get("unit", "").lower()):
            return {"status":"unavailable", "value":None,
                    "currency":wage["currency"], "unit":"per_year",
                    "kind":"hourly_source_not_annualized",
                    "reference_period":wage["period"], "source":wage["source"],
                    "hourly_optional":wage["value"],
                    "hourly_kind":"reported_hourly",
                    "payments_per_year":None, "payments_verified":False,
                    "precision":wage.get("precision"),
                    "reason":"Verified source wage is hourly; annual working hours are not assumed.",
                    "note":"The published hourly wage remains available in national_occupation_wage."}
    # A major-group average must not enter the profession-specific salary card.
    # Group data remain accessible independently in national_major_group_context.
    return {"status":"unavailable", "value":None, "unit":"per_year",
            "precision":"exact_occupation",
            "reason":"No verified salary specific to the selected occupation",
            "major_group_context_available":group_context.get("status") == "available",
            "note":"The ISCO-08 major-group mean is not a wage for this occupation."}



def history(country, occupation, start_year, end_year):
    """Separate history tab; never merge group observations with exact wages."""
    code = country.upper()
    if code not in COUNTRY_MAP:
        raise LookupError("Unknown country")
    if occupation not in JOBS:
        raise ValueError("Unknown occupation")
    if not 1900 <= start_year <= end_year <= 2100 or end_year-start_year > 100:
        raise ValueError("Invalid history year range")
    group = JOBS[occupation]["isco08_major_group"]
    return {"country":code, "occupation":occupation,
            "start_year":start_year, "end_year":end_year,
            "exact_occupation_history":exact_history(code, occupation, start_year, end_year),
            "major_group_history":group_history(code, group, start_year, end_year),
            "note":"Group series is independent and cannot be relabelled as exact occupation salary."}


def region_check(country, region):
    if not region:
        return None
    data = region_configuration(country)
    options = {r["code"] for r in data["options"]}
    if region not in options:
        raise ValueError("Region is not listed for the selected country")
    return region


def wage_for(country, occupation):
    if country == "BR":
        official = br_rais_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country in ("US", "CA"):
        return na.wages(country, occupation)
    if country == "PT":
        official = pt_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country == "GB":
        official = uk_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country == "DE":
        official = de_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country == "FR":
        official = fr_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country == "NL":
        official = nl_wages.wages(country, occupation)
        if official.get("status") != "unavailable":
            return official
    if country == "IT":
        official = it_wages.occupation_wage(occupation)
        if official.get("status") != "unavailable":
            return official
    return ilostat_salary(country, occupation)


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
        result = tax_components(country, annual_gross, tax_year=tax_year,
                                province=region if country == "CA" else None)
        if country == "US":
            result["state_wage_income_tax"] = state_wage_income_tax(region, tax_year, annual_gross)
        return result
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
    from app.us_oews import curated_state_wages
    regional_wage = (curated_state_wages(occupation, region) if code == "US" and region
                     else ca_province.wage(occupation, region) if code == "CA" and region
                     else br_rais_states.wage(occupation, region) if code == "BR" and region
                     else de_entgeltatlas_states.wage(occupation, region) if code == "DE" and region
                     else {"status": "not_requested" if code in ("US", "CA", "BR", "DE") else "not_applicable"})
    major_group = JOBS[occupation]["isco08_major_group"]
    group_context = (
        ca_groups.context(occupation) if code == "CA" else
        ie_groups.context(occupation, major_group) if code == "IE" else
        group_salary(code, major_group) if major_group else {
            "status": "unavailable", "precision": "isco08_major_group",
            "reason": "No validated occupational-group mapping"
        }
    )
    swiss_context = (ch_wages.context(occupation) if code == "CH" else
                     {"status":"not_applicable"})
    italy_context = (it_wages.context(
        occupation, major_group,
        JOBS[occupation].get("major_group_caution")
    ) if code == "IT" else {"status":"not_applicable"})
    ireland_public_entry = (ie_wages.wage(occupation) if code == "IE" else
                            {"status":"not_applicable"})
    ireland_group_context = ie_groups.context(occupation, major_group) if code == "IE" else {"status":"not_applicable"}
    brazil_cbo = br_cbo.mapping(occupation) if code == "BR" else {"status":"not_applicable"}
    brazil_public_entry = br_public_wages.wage(occupation) if code == "BR" else {"status":"not_applicable"}
    portugal_public_entry = pt_public_wages.wage(occupation) if code == "PT" else {"status":"not_applicable"}
    exact_available = wage.get("status") == "available"
    group_available = (
        group_context.get("status") == "available" and (
            any(v.get("status") == "available"
                for v in group_context.get("values", {}).values())
            if group_context.get("values") is not None
            else bool(group_context.get("observations"))
        )
    )
    display_source = (
        "exact_occupation" if exact_available else
        "occupational_group_context" if group_available and code == "CA" else
        "isco08_major_group_context" if group_available else
        "unavailable"
    )
    warnings = []
    if code == "US":
        warnings.append("Federal components and selected state wage/payroll components only; complete state and local tax models are not implemented.")
    elif code == "CA":
        warnings.append("Federal/provincial income tax models are not implemented; Quebec payroll differs.")
    if wage.get("status") == "available":
        warnings.append("National occupational observation; it is not a capital-city salary or a job offer.")
        warnings.append("The wage source reference period is distinct from any 2026 tax scenario.")
    else:
        warnings.append("No matching verified occupational observation; no wage has been inferred.")
    warnings.append("Broad occupational-group earnings are contextual only, not the selected profession's salary or a substitute for missing exact wages.")
    if code == "IN":
        warnings.append("PLFS 2025 employee earnings are all-occupation context only, not a wage for the selected occupation or state.")
    warnings.append("Cost-of-living basket and net purchasing-power comparison are not yet available.")
    return {
        "country": {"code": code, "name": selected["name"],
                    "capital": selected["capital"], "currency": selected["currency"]},
        "occupation": {"id": occupation, "label": JOBS[occupation]["translations"]["en"],
                       "translations": JOBS[occupation]["translations"],
                       "isco08": JOBS[occupation]["isco08"]},
        "region": {"selected": region, "ui": region_configuration(code, region, tax_year, annual_gross),
                   "regional_tax_model_status": ("wage_income_tax_only" if code == "US" and region and
                     state_wage_income_tax(region, tax_year, annual_gross).get("status") == "available"
                     else "partial_components" if code == "US" and region and
                     state_wage_income_tax(region, tax_year, annual_gross).get("status") == "partial_components"
                     else "not_implemented" if code in ("US","CA") else "not_applicable")},
        "national_occupation_wage": wage,
        "india_plfs_employee_earnings_context": (in_plfs.earnings() if code == "IN" else {"status": "not_applicable"}),
        "india_nco2015_professional_group_context": (in_nco_crosswalk.context(occupation) if code == "IN" else {"status": "not_applicable"}),
        "india_nco2015_regional_group_context": (in_nco_crosswalk.context(occupation, region) if code == "IN" and region else {"status": "not_requested" if code == "IN" else "not_applicable"}),
        "regional_occupation_wage": regional_wage,
        "national_major_group_context": group_context,
        "swiss_ch_isco19_submajor_context": swiss_context,
            "italy_cp2021_major_group_context": italy_context,
        "ireland_public_sector_entry": ireland_public_entry,
        "ireland_cso_occupational_group_context": ireland_group_context,
        "brazil_cbo_occupation": brazil_cbo,
        "brazil_public_sector_entry": brazil_public_entry,
        "portugal_public_sector_entry": portugal_public_entry,
        "annual_presentation": annual_presentation(wage, group_context),
        "salary_display": {
            "source": display_source,
            "status": "available" if exact_available else "unavailable",
            "major_group_context_available": group_available,
            "precision": "occupation" if exact_available else
                         group_context.get("precision") if group_available else None,
            "isco08_major_group": major_group,
            "group_mapping_caution": JOBS[occupation]["group_mapping_caution"],
            "note": ("Group earnings are context only, not the salary of this occupation."
                     if display_source in ("occupational_group_context", "isco08_major_group_context") else
                     "Exact occupation observation shown; group context remains separate."
                     if exact_available else "No validated earnings available."),
        },
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


def regional_salary_coverage(country):
    """Actual exact occupation/region cells; no national, metro or group proxies."""
    if country == "DE":
        from app.de_entgeltatlas_states import STATES
        names = {code: item[0] for code, item in STATES.items()}
        cells = list(de_entgeltatlas_states.DATA)
        kind = "federal_state"
    elif country == "BR":
        from app.br_rais_states_import import UF
        names = UF
        cells = list(br_rais_states.DATA)
        kind = "state"
    elif country == "CA":
        from app.ca_province_wages import init as init_ca, PROVINCES
        from app.store import connect
        with connect() as db:
            init_ca(db)
            cells = db.execute("""
                SELECT occupation, province FROM ca_province_wages
                GROUP BY occupation, province
                HAVING COUNT(DISTINCT unit)=1
            """).fetchall()
        names = PROVINCES
        kind = "province_or_territory"
    elif country == "US":
        from app.us_oews import init as init_us
        from app.north_america import US_SOC
        from app.client_config import REGIONS
        from app.store import connect
        names = dict(REGIONS["US"]["options"])
        # An imported SOC may be used by more than one approved interface title.
        jobs_by_soc = {}
        for occupation, (soc, _) in US_SOC.items():
            jobs_by_soc.setdefault(soc, set()).add(occupation)
        with connect() as db:
            init_us(db)
            raw = db.execute("""
                SELECT occ_code, prim_state, published_year,
                       COUNT(DISTINCT area || ':' || area_title || ':' ||
                           COALESCE(CAST(a_mean AS TEXT), '') || ':' ||
                           COALESCE(CAST(a_median AS TEXT), '') || ':' ||
                           COALESCE(CAST(h_mean AS TEXT), '') || ':' ||
                           COALESCE(CAST(h_median AS TEXT), '')) AS variants
                FROM us_oews
                WHERE area_type IN ('2','2.0')
                  AND o_group='detailed' AND naics IN ('000000','0')
                  AND (i_group IN ('cross-industry','cross_industry','') OR i_group IS NULL)
                  AND own_code IN ('1235','')
                  AND (a_mean IS NOT NULL OR a_median IS NOT NULL
                       OR h_mean IS NOT NULL OR h_median IS NOT NULL)
                GROUP BY occ_code, prim_state, published_year
            """).fetchall()
        latest = {}
        for soc, region, year, variants in raw:
            if region not in names or soc not in jobs_by_soc:
                continue
            key = (soc, region)
            if key not in latest or year > latest[key][0]:
                latest[key] = (year, variants)
        cells = [(job, region) for (soc, region), (_, variants) in latest.items()
                 if variants == 1 for job in jobs_by_soc[soc]]
        kind = "state"
    else:
        return {"status": "not_applicable", "region_type": None}
    by_region = []
    for region, name in names.items():
        occupations = sorted({job for job, code in cells if code == region})
        by_region.append({"code": region, "name": name,
                          "observed_occupations": len(occupations),
                          "possible_occupations": len(JOBS),
                          "status": "partial" if occupations else "unavailable"})
    covered = {occupation for occupation, region in cells if region in names}
    valid_cells = {(occupation, region) for occupation, region in cells if region in names}
    return {
        "status": "partial" if valid_cells else "unavailable",
        "region_type": kind,
        "regions_with_data": sum(r["observed_occupations"] > 0 for r in by_region),
        "possible_regions": len(names),
        "observed_occupations": len(covered),
        "possible_occupations": len(JOBS),
        "observed_occupation_region_pairs": len(valid_cells),
        "possible_occupation_region_pairs": len(JOBS) * len(names),
        "by_region": by_region,
        "note": "Only imported, exact occupation-region observations. National wages and occupational groups do not count.",
    }


def coverage():
    """Coverage by independent salary layer: occupation, group context and public-sector entry."""
    observed = {(c["country"], c["occupation"]): c["latest_period"]
                for c in ilostat_availability()["cells"] if c["status"] == "available"}
    observed.update(na.observed_coverage())
    observed.update({key: period for key, (_count, period) in pt_wages.observed_coverage().items()})
    observed.update({("GB", key): period for key, (_count, period) in uk_wages.observed_coverage().items()})
    observed.update({("DE", key): period for key, (_count, period) in de_wages.observed_coverage().items()})
    observed.update({("FR", key): period for key, (_count, period) in fr_wages.observed_coverage().items()})
    observed.update({("NL", key): period for key, (_count, period) in nl_wages.observed_coverage().items()})
    observed.update({("IT", key): period for key, period in it_wages.observed_coverage().items()})

    observed.update(br_rais_wages.observed_coverage())

    public_ie = ie_wages.public_sector_coverage()
    public_br = br_public_wages.public_sector_coverage()
    public_pt = pt_public_wages.public_sector_coverage()
    rows = []
    for code in COUNTRY_MAP:
        exact_count = sum(country == code for country, _occupation in observed)
        group_count = 0
        for occupation, job in JOBS.items():
            major = job["isco08_major_group"]
            if not major:
                continue
            context = (ie_groups.context(occupation, major) if code == "IE"
                       else ca_groups.context(occupation) if code == "CA"
                       else group_salary(code, major))
            if context.get("status") == "available":
                group_count += 1
        public_count = (len(public_ie) if code == "IE" else
                        len(public_br) if code == "BR" else
                        len(public_pt) if code == "PT" else 0)
        rows.append({
            "code": code,
            "observed_occupations": exact_count,
            "group_context_occupations": group_count,
            "public_sector_entry_occupations": public_count,
            "possible_occupations": len(OCCUPATIONS),
            "regional_salary_coverage": regional_salary_coverage(code),
            "status": "partial" if (exact_count or group_count or public_count) else "unavailable",
        })
    return {
        "countries": len(COUNTRY_MAP), "occupations": len(OCCUPATIONS),
        "possible_pairs": len(COUNTRY_MAP) * len(OCCUPATIONS),
        "observed_pairs": len(observed),
        "layers": ["observed_occupation", "observed_group", "public_sector_entry"],
        "by_country": rows,
        "note": "The three layers are independent. Group and public-sector values never count as exact occupation observations.",
    }

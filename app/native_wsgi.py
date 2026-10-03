"""Native WSGI HTTP adapter for CloudLinux Passenger/LiteSpeed.

Does not import FastAPI or a2wsgi. Reuses EarnWage's validated business modules.
FastAPI app.main remains for local ASGI / existing API tests.
"""
import asyncio
import json
import logging
import os
import hmac
import unicodedata
import threading
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import parse_qs

from app.catalog import COUNTRY_MAP, OCCUPATIONS, SUPPORTED_LANGUAGES
from app import earnwage_queries as ew
from app import north_america as na
from app import ca_province_wages
from app import us_oews
from app import jobs
from app.client_config import configuration, region_configuration
from app.ilostat_import import (
    TOC, earnings_datasets, availability, load_snapshot, catalogue_rows,
)
from app.providers import UpstreamUnavailable, exchange_rate, inflation_series
from app.release import COMMIT, ready
from app.store import connect
from app.tax_components import components as tax_components

VERSION = "0.5.20"
ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger("earnwage.wsgi")
JOBS = {job["id"]: job for job in OCCUPATIONS}
INITIALIZED = False
INIT_LOCK = threading.Lock()
HTTP_STATUS = {
    200: "200 OK", 204: "204 No Content", 400: "400 Bad Request", 404: "404 Not Found",
    405: "405 Method Not Allowed", 413: "413 Content Too Large",
    422: "422 Unprocessable Entity", 503: "503 Service Unavailable",
    401: "401 Unauthorized", 403: "403 Forbidden", 409: "409 Conflict",
    500: "500 Internal Server Error",
}


class ApiError(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def initialize():
    """Load real committed snapshots once per Passenger worker process."""
    global INITIALIZED
    if INITIALIZED:
        return
    with INIT_LOCK:
        if INITIALIZED:
            return
        with connect():
            pass
        load_snapshot(ROOT / "data" / "salaries_snapshot.json")
        na.load_snapshot(ROOT / "data" / "north_america_wages.json")
        ca_province_wages.load_snapshot(ROOT / "data" / "ca_province_wages.json")
        from app.us_oews_snapshot import load_snapshot as load_us_oews_snapshot
        load_us_oews_snapshot(ROOT / "data" / "us_oews_curated.json")
        from app.in_plfs_microdata import load_snapshot as load_india_plfs
        load_india_plfs(ROOT / "data" / "in_plfs_2025_nco.json")
        from app import br_rais_states
        br_rais_states.load()
        from app.pt_occupation_wages import load_snapshot as load_pt_wages
        load_pt_wages()
        from app.uk_ashe_wages import load_snapshot as load_uk_wages
        load_uk_wages()
        from app.de_entgeltatlas_wages import load_snapshot as load_de_wages
        load_de_wages()
        from app import de_entgeltatlas_states
        de_entgeltatlas_states.load()
        from app.fr_insee_wages import load_snapshot as load_fr_wages
        load_fr_wages()
        from app.nl_cbs_wages import load_snapshot as load_nl_wages
        load_nl_wages()
        INITIALIZED = True


def reply(start_response, payload, code=200, method="GET", origin=None):
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ]
    headers.append(("Vary", "Origin"))
    if origin == "https://gilpereirapt.github.io":
        headers.append(("Access-Control-Allow-Origin", origin))
    start_response(HTTP_STATUS[code], headers)
    return [] if method == "HEAD" else [body]


def one(params, name, default=None):
    values = params.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise ApiError(422, "Supply one value for " + name)
    return values[0]


def country(value):
    code = str(value or "").upper()
    if code not in COUNTRY_MAP:
        raise ApiError(404, "Unknown country")
    return code


def occupation(value):
    if value not in JOBS:
        raise ApiError(422, "Unknown occupation")
    return value


def integer(params, name, default):
    try:
        return int(one(params, name, default))
    except (TypeError, ValueError):
        raise ApiError(422, "Invalid integer: " + name)


def boolean(params, name, default=False):
    text = str(one(params, name, str(default))).lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise ApiError(422, "Invalid boolean: " + name)



def recent_jobs(result, max_age_days, limit):
    """Filter known old publication dates, without mistaking fetch time for age."""
    now = datetime.now(timezone.utc)
    kept, excluded = [], 0
    for job in result["jobs"]:
        published = job.get("published_at") if job.get("publication_date_status") != "unknown" else None
        try:
            date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            age = max(0, (now - date.astimezone(timezone.utc)).days)
        except (AttributeError, TypeError, ValueError, OverflowError):
            age = None
        if max_age_days and age is not None and age > max_age_days:
            excluded += 1
            continue
        salary = job.get("salary_text")
        structured = job.get("salary_structured")
        salary_display = salary.strip() if isinstance(salary, str) and salary.strip() else "N\u00e3o divulgado"
        kept.append({**job, "age_days": age,
                     "salary_display": salary_display,
                     "salary_disclosed": bool(salary_display != "N\u00e3o divulgado" or structured),
                     "publication_date_status": job.get("publication_date_status", "reported") if age is not None else "unknown"})
    updated = {**result, "jobs": kept[:limit], "count": len(kept),
            "returned": min(len(kept), limit),
            "status": "available" if kept else "no_results",
            "max_age_days": max_age_days,
            "excluded_by_age": excluded,
            "publication_date_note": "Provider-reported dates may be original creation or last update; unknown dates are retained and labelled."}
    if "jobs_after_filter" in updated:
        updated["jobs_after_country_occupation_filter"] = result["jobs_after_filter"]
        updated["jobs_after_filter"] = len(kept)
        updated["jobs_after_age_filter"] = len(kept)
        for board, stats in updated.get("board_stats", {}).items():
            stats["jobs_after_country_occupation_filter"] = stats["jobs_after_filter"]
            stats["jobs_after_age_filter"] = sum(job["id"].split(":", 2)[1] == board for job in kept)
            stats["jobs_after_filter"] = stats["jobs_after_age_filter"]
    if "remote_unverified" in result:
        remote = recent_jobs({"jobs": result["remote_unverified"]}, max_age_days, limit)
        updated["remote_unverified"] = remote["jobs"]
        updated["remote_unverified_count"] = remote["count"]
        updated["remote_unverified_excluded_by_age"] = remote["excluded_by_age"]
    return updated


def gross(params, name):
    raw = one(params, name)
    if raw is None:
        return None
    try:
        from decimal import Decimal
        amount = Decimal(raw)
        if not amount.is_finite() or not 0 < amount <= 100000000:
            raise ValueError()
        return float(amount)
    except (ValueError, TypeError, ArithmeticError):
        raise ApiError(422, "Invalid annual gross salary: " + name)


def run_async(awaitable):
    """Only external-data routes use an event loop; no ASGI adapter is involved."""
    return asyncio.run(awaitable)


def sources():
    return {
        "irs_2026_federal_tax": {
            "url": "https://www.irs.gov/irb/2025-45_IRB",
            "role": "2026 US federal single tax brackets and standard deduction",
            "status": "partial illustration implemented",
        },
        "cra_2026_cpp_ei": {
            "url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032oc-jan/t4032oc-january-general-information.html",
            "role": "2026 CPP, CPP2, EI outside Quebec",
            "status": "partial illustration implemented",
        },
        "canada_job_bank_wages": {"url": na.CANADA_URL,
            "role": "Canadian national occupational wages", "status": "verified subset imported"},
        "us_bls_oews": {"url": na.BLS_TABLE,
            "role": "US national occupation wages", "status": "verified subset imported"},
        "himalayas_jobs": {"url": "https://himalayas.app/jobs/api", "role": "Attributed remote vacancies", "status": "integrated"},
        "jobicy_jobs": {"url": "https://jobicy.com/api/v2/remote-jobs", "role": "Attributed remote vacancies", "status": "integrated"},
        "remoteok_jobs": {"url": "https://remoteok.com/api", "role": "Attributed remote vacancies", "status": "integrated"},
        "remotive_jobs": {"url": "https://remotive.com/remote-jobs/api",
            "role": "Remote-only attributed job listings", "status": "integrated"},
        "ilostat": {"url": TOC, "role": "Official occupation earnings",
            "status": "offline importer; source availability not guaranteed"},
        "ba_entgeltatlas": {"url": "https://www.arbeitsagentur.de/hilfe-entgeltatlas",
            "role": "Germany national 2025 occupation-specific monthly median gross remuneration",
            "status": "27 approved direct Berufsgattung mappings imported"},
        "insee_fr_detailed_wages": {"url": "https://www.data.gouv.fr/datasets/salaires-dans-le-secteur-prive-par-categorie-socioprofessionnelle-detaillee",
            "role": "France 2024 detailed PCS-ESE mean net monthly EQTP salaries for private employees",
            "status": "23 approved direct PCS-ESE mappings imported"},
        "cbs_nl_occupation_wages": {"url": "https://www.cbs.nl/nl-nl/cijfers/detail/86355NED",
            "role": "Netherlands employee median gross hourly wage by BRC occupational group",
            "status": "21 approved BRC mappings imported; 2025 provisional where published, otherwise 2024 definitive"},
        "eurostat_hicp": {
            "url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr",
            "role": "National monthly inflation", "status": "integrated"},
        "ecb_exr": {"url": "https://data-api.ecb.europa.eu/service/data/EXR",
            "role": "Reference exchange rates", "status": "integrated"},
        "esco": {"url": "https://ec.europa.eu/esco/api/",
            "role": "Occupation translations", "status": "planned"},
        "oecd": {"url": "https://sdmx.oecd.org/public/rest/v1/",
            "role": "National wages and taxing wages", "status": "planned"},
    }


def dispatch(path, q):
    if path in ("/", "/v1/health"):
        if path == "/v1/health" and not ready():
            raise ApiError(503, "Application stores unavailable")
        return {"status": "ok", "version": VERSION, "commit": COMMIT,
                "service": "EarnWage API",
                "runtime": "native_wsgi"} if path == "/v1/health" else {
                    "service": "EarnWage API", "version": VERSION,
                    "health": "/v1/health", "documentation": "See README.md in GitHub"}
    if path == "/v1/app-config":
        return configuration()
    if path == "/v1/data-inventory":
        from app.data_inventory import build_inventory
        return build_inventory()
    if path == "/v1/earnwage/coverage":
        return ew.coverage()
    if path == "/v1/earnwage/history":
        return ew.history(country(one(q, "country")),
                          occupation(one(q, "occupation")),
                          integer(q, "start_year", 2015),
                          integer(q, "end_year", 2025))
    if path == "/v1/earnwage/overview":
        return ew.overview(country(one(q, "country")),
                           occupation(one(q, "occupation")),
                           one(q, "region"), gross(q, "annual_gross"),
                           integer(q, "tax_year", 2026))
    if path == "/v1/earnwage/compare":
        return ew.compare(country(one(q, "country_a")),
                          country(one(q, "country_b")),
                          occupation(one(q, "occupation")),
                          one(q, "region_a"), one(q, "region_b"),
                          gross(q, "annual_gross_a"), gross(q, "annual_gross_b"),
                          integer(q, "tax_year", 2026))
    if path == "/v1/eurostat/coverage":
        from app.eurostat_economy import EUROSTAT_COUNTRIES, SERIES, ensure_tables, read
        from app.country_insights_store import connect as insights_connect
        with insights_connect() as db:
            ensure_tables(db)
            rows = [{"country": code,
                     "indicators": {name: read(db, code, name) for name in SERIES}}
                    for code in EUROSTAT_COUNTRIES]
        return {"countries": rows, "count": len(rows),
                "note": "Coverage is per dataset, not a guarantee of a current observation."}
    if path == "/v1/eurostat/compare":
        from app.eurostat_economy import EUROSTAT_COUNTRIES, SERIES, ensure_tables, read
        from app.country_insights_store import connect as insights_connect
        a, b = country(one(q, "country_a")), country(one(q, "country_b"))
        if a not in EUROSTAT_COUNTRIES or b not in EUROSTAT_COUNTRIES:
            raise ApiError(422, "Eurostat country not supported")
        if a == b:
            raise ApiError(422, "Supply two different countries")
        with insights_connect() as db:
            ensure_tables(db)
            rows = [{"country": code,
                     "indicators": {name: read(db, code, name) for name in SERIES}}
                    for code in (a, b)]
        return {"countries": rows, "note": "Compare matching periods and identical indicator definitions; net earnings are a reference scenario, not a personal net salary."}
    if path.startswith("/v1/eurostat/") and len(path.split("/")) == 5:
        from app.eurostat_economy import EUROSTAT_COUNTRIES, SERIES, ensure_tables, read
        from app.country_insights_store import connect as insights_connect
        parts_eu = path.split("/")
        code, name = country(parts_eu[3]), parts_eu[4]
        if code not in EUROSTAT_COUNTRIES or name not in SERIES:
            raise ApiError(404, "Unknown Eurostat country or indicator")
        with insights_connect() as db:
            ensure_tables(db)
            return read(db, code, name)
    if path == "/v1/economy/coverage":
        from app.country_insights import ISO3
        from app.country_insights_store import connect, read_indicator
        names = ("inflation_annual", "ppp_private_consumption")
        with connect() as db:
            rows = []
            for code in ISO3:
                metrics = {name: read_indicator(db, code, name) for name in names}
                rows.append({"country": code, "currency": COUNTRY_MAP[code]["currency"],
                             "indicators": metrics})
        return {"countries": rows, "count": len(rows),
                "note": "Annual CPI inflation and household consumption PPP are distinct measures; observation years may differ."}
    if path == "/v1/economy/compare":
        from app.country_insights_store import connect, read_indicator
        first, second = country(one(q, "country_a")), country(one(q, "country_b"))
        names = ("inflation_annual", "ppp_private_consumption")
        with connect() as db:
            rows = [{"country": code, "currency": COUNTRY_MAP[code]["currency"],
                     "indicators": {name: read_indicator(db, code, name) for name in names}}
                    for code in (first, second)]
        return {"countries": rows, "note": "PPP private consumption is local currency per international dollar. Do not divide two wages without matching years and verified units; this is not a city cost-of-living estimate."}
    if path == "/v1/indicators":
        from app.country_insights import INDICATORS
        return {"indicators": [{"name": name, "code": code, "unit": unit}
                for name, (code, unit) in INDICATORS.items()],
                "safety": {"name": "Gallup Law and Order Index",
                           "status": "not_connected",
                           "alternative_sdg": "16.1.4"}}
    if path == "/v1/compare/indicators":
        from app.country_insights import country_insights
        raw = one(q, "countries")
        if not raw:
            raise ApiError(422, "countries is required (e.g. PT,DE,US)")
        codes = [country(item.strip()) for item in raw.split(",")]
        if not 2 <= len(codes) <= 5 or len(set(codes)) != len(codes):
            raise ApiError(422, "Supply 2 to 5 distinct supported countries")
        return {"countries": [country_insights(code) for code in codes],
                "note": "Compare matching indicators with their individual reference years; no composite ranking."}
    parts_insights = [p for p in path.split("/") if p]
    if len(parts_insights) >= 4 and parts_insights[:2] == ["v1", "countries"] and parts_insights[3] == "indicators":
        from app.country_insights import country_insights, indicator, safety
        code = country(parts_insights[2])
        if len(parts_insights) == 4:
            return country_insights(code)
        if len(parts_insights) == 5:
            if parts_insights[4] == "safety":
                return safety(code)
            year_raw = one(q, "year")
            year = integer(q, "year", None) if year_raw is not None else None
            return indicator(code, parts_insights[4], year=year,
                             history=boolean(q, "history", False))
        raise ApiError(404, "Unknown indicator route")
    if path == "/v1/countries":
        return {"countries": list(COUNTRY_MAP.values()), "count": len(COUNTRY_MAP)}
    if path == "/v1/languages":
        return {"languages": [{"code": k, "label": v} for k, v in SUPPORTED_LANGUAGES.items()],
                "default": "en", "portuguese_locale": "pt",
                "note": "Occupation labels localized in seven supported languages; other interface text may require client localization."}
    if path == "/v1/sources":
        return sources()
    if path == "/v1/salaries/groups/coverage":
        from app.ilostat_groups import group_coverage
        return group_coverage()
    if path == "/v1/salaries/availability/matrix":
        lang = str(one(q, "lang", "en")).split("-")[0].lower()
        if lang not in SUPPORTED_LANGUAGES:
            raise ApiError(422, "Unsupported interface language")
        labels = {j["id"]: (j["translations"].get(lang) or j["translations"]["en"]) for j in OCCUPATIONS}
        result = availability()
        result["language"] = lang
        for cell in result["cells"]:
            cell["occupation_label"] = labels[cell["occupation"]]
        observations = na.observed_coverage()
        from app import uk_ashe_wages, de_entgeltatlas_wages, fr_insee_wages, nl_cbs_wages
        uk = uk_ashe_wages.observed_coverage()
        de = de_entgeltatlas_wages.observed_coverage()
        fr = fr_insee_wages.observed_coverage()
        nl = nl_cbs_wages.observed_coverage()
        for cell in result["cells"]:
            period = observations.get((cell["country"], cell["occupation"]))
            if period is not None:
                cell.update(status="available", latest_period=period,
                            source_family="north_america_official_wages")
            elif cell["country"] == "GB" and cell["occupation"] in uk:
                cell.update(status="available", latest_period=uk[cell["occupation"]][1],
                            source_family="ons_ashe_soc2020")
            elif cell["country"] == "DE" and cell["occupation"] in de:
                cell.update(status="available", latest_period=de[cell["occupation"]][1],
                            source_family="ba_entgeltatlas_kldb")
            elif cell["country"] == "FR" and cell["occupation"] in fr:
                cell.update(status="available", latest_period=fr[cell["occupation"]][1],
                            source_family="insee_pcs_ese_private")
            elif cell["country"] == "NL" and cell["occupation"] in nl:
                cell.update(status="available", latest_period=nl[cell["occupation"]][1],
                            source_family="cbs_brc_hourly_median")
        result["available_cells"] = sum(c["status"] == "available" for c in result["cells"])
        return result
    if path == "/v1/occupations":
        lang = str(one(q, "lang", "en")).split("-")[0].lower()
        if lang not in SUPPORTED_LANGUAGES:
            raise ApiError(422, "Unsupported interface language")
        term = str(one(q, "q", "")).casefold()
        term = "".join(ch for ch in unicodedata.normalize("NFKD", term)
                       if not unicodedata.combining(ch)).strip()
        if len(term) > 100:
            raise ApiError(422, "Search term too long")
        items = []
        for j in OCCUPATIONS:
            terms = [j["id"], *j["translations"].values(),
                     *(alias for group in j.get("aliases", {}).values() for alias in group)]
            normalized = ["".join(ch for ch in unicodedata.normalize("NFKD", value.casefold())
                                  if not unicodedata.combining(ch)) for value in terms]
            if term and not any(term in value for value in normalized):
                continue
            items.append({"id": j["id"], "isco08": j["isco08"],
                          "label": (j["translations"].get(lang) or j["translations"]["en"]),
                          "isco08_major_group": j["isco08_major_group"],
                          "group_mapping_caution": j["group_mapping_caution"],
                          "translations": j["translations"],
                          "aliases": j.get("aliases", {})})
        return {"language": lang, "fallback": "en", "count": len(items), "occupations": items}
    if path == "/v1/compare":
        a, b = country(one(q, "country_a")), country(one(q, "country_b"))
        job = one(q, "occupation")
        if job is not None:
            occupation(job)
        def side(code):
            item = COUNTRY_MAP[code].copy()
            item["salary"] = ew.wage_for(code, job) if job else {
                "status": "unavailable", "reason": "Select an occupation"}
            item["tax"] = {"status": "unavailable",
                           "reason": "Country-specific model not validated"}
            item["capital_cost_of_living"] = {"status": "unavailable",
                                              "reason": "No verified capital-level series"}
            if item["inflation_provider"] == "eurostat":
                item["inflation"] = {"status": "available", **run_async(inflation_series(code))}
            else:
                item["inflation"] = {"status": "unavailable",
                                     "reason": "Validated importer pending"}
            return item
        return {"version": VERSION, "country_a": side(a), "country_b": side(b),
                "occupation": job,
                "comparison_note": "National inflation is not city cost of living; no inferred net salary."}
    if path == "/v1/es/earnings/groups":
        from app.es_eaes_groups import catalogue
        return catalogue()
    if path.startswith("/v1/es/earnings/groups/") and len(path.split("/")) == 6:
        from app.es_eaes_groups import group_history
        group = path.rsplit("/", 1)[-1]
        try:
            return group_history(group,
                                 one(q, "sex", "both"),
                                 integer(q, "start_year", 2008),
                                 integer(q, "end_year", 2024))
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    parts = [p for p in path.split("/") if p]
    if len(parts) == 3 and parts[:2] == ["v1", "countries"]:
        return COUNTRY_MAP[country(parts[2])]
    if len(parts) == 3 and parts[:2] == ["v1", "regions"]:
        return region_configuration(country(parts[2]))
    if len(parts) == 3 and parts[:2] == ["v1", "inflation"]:
        code = country(parts[2])
        if COUNTRY_MAP[code]["inflation_provider"] != "eurostat":
            return {"country": code, "status": "unavailable",
                    "reason": "No validated free national importer"}
        return {"status": "available", **run_async(inflation_series(code))}
    if len(parts) == 3 and parts[:2] == ["v1", "exchange-rates"]:
        currency = parts[2].upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ApiError(422, "Invalid ISO currency")
        value = run_async(exchange_rate(currency))
        return {"currency": currency, "status": "unavailable",
                "reason": "No ECB reference series for this currency"} if value is None else {
                    "status": "available", **value}
    if len(parts) == 5 and parts[:3] == ["v1", "salaries", "groups"]:
        from app.ilostat_groups import group_salary
        return group_salary(country(parts[3]), parts[4])
    if len(parts) == 4 and parts[:2] == ["v1", "salaries"]:
        c, job = country(parts[2]), occupation(parts[3])
        return ew.wage_for(c, job)
    if len(parts) == 6 and parts[:4] == ["v1", "us", "oews", "states"]:
        try:
            return us_oews.curated_state_wages(occupation(parts[4]), parts[5])
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    if path == "/v1/de/entgeltatlas/regional/coverage":
        from app.de_entgeltatlas_states import coverage
        return coverage()
    if path == "/v1/pt/public-sector/occupations":
        from app.pt_public_wages import occupation_matrix
        return occupation_matrix()
    if path == "/v1/pt/public-sector/coverage":
        from app.pt_public_wages import coverage
        return coverage()
    if path == "/v1/br/rais/regional/coverage":
        from app.br_rais_states import coverage
        return coverage()
    if path == "/v1/in/earnwage-nco/coverage":
        from app.in_nco_crosswalk import coverage
        return coverage()
    if len(parts) == 4 and parts[:3] == ["v1", "in", "earnwage-nco"]:
        from app.in_nco_crosswalk import context
        try:
            return context(occupation(parts[3]), one(q, "state"))
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    if path == "/v1/in/plfs/nco/coverage":
        from app.in_plfs_microdata import coverage
        return coverage()
    if len(parts) == 5 and parts[:4] == ["v1", "in", "plfs", "nco"]:
        from app.in_plfs_microdata import wages
        try:
            return wages(parts[4], one(q, "state"))
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    if path == "/v1/in/plfs/earnings":
        from app.in_plfs import earnings
        return earnings()
    if path == "/v1/in/wage-sources":
        from app.in_plfs import wage_sources
        return wage_sources()
    if path == "/v1/ca/provinces/coverage":
        return ca_province_wages.coverage()
    if len(parts) == 5 and parts[:3] == ["v1", "ca", "provinces"]:
        try:
            return ca_province_wages.wage(occupation(parts[3]), parts[4])
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    if path == "/v1/us/oews/coverage":
        return us_oews.coverage()
    if path == "/v1/us/oews/occupations":
        term = one(q, "q")
        if term is not None and len(term) > 100:
            raise ApiError(422, "Search term too long")
        limit = integer(q, "limit", 100)
        offset = integer(q, "offset", 0)
        if not 1 <= limit <= 500 or offset < 0:
            raise ApiError(422, "Invalid pagination")
        return us_oews.catalogue(q=term, limit=limit, offset=offset)
    if len(parts) == 5 and parts[:4] == ["v1", "us", "oews", "wages"]:
        year_raw = one(q, "year")
        try:
            year = int(year_raw) if year_raw is not None else None
            return us_oews.wages(parts[4], state=one(q, "state"),
                                 area=one(q, "area"), year=year)
        except ValueError as exc:
            raise ApiError(422, str(exc)) from exc
    if len(parts) == 4 and parts[:2] == ["v1", "wages"]:
        return na.wages(country(parts[2]), occupation(parts[3]))
    if len(parts) == 3 and parts[:2] == ["v1", "tax-components"]:
        c = country(parts[2])
        annual = gross(q, "annual_gross")
        if annual is None:
            raise ApiError(422, "annual_gross is required")
        return tax_components(c, annual, tax_year=integer(q, "tax_year", 2026),
                              filing_status=one(q, "filing_status", "single"),
                              province=(str(one(q, "province")).upper()
                                        if one(q, "province") else None))
    if path == "/v1/ilostat/datasets":
        try:
            datasets = earnings_datasets(catalogue_rows())
        except Exception as exc:
            raise UpstreamUnavailable("ILOSTAT catalogue unavailable") from exc
        return {"source_url": TOC, "datasets":
                datasets}
    if path == "/v1/jobs/dictionary":
        from app.job_dictionary import dictionary
        code = one(q, "country")
        return dictionary(occupation(one(q, "occupation")), country(code) if code else None)
    if path == "/v1/jobs":
        c, job = country(one(q, "country")), occupation(one(q, "occupation"))
        limit = integer(q, "limit", 20)
        if not 1 <= limit <= 100:
            raise ApiError(422, "limit must be between 1 and 100")
        provider = str(one(q, "provider", "all")).lower()
        if provider not in ("all", "remotive", "arbeitnow", "himalayas", "jobicy", "remoteok", "greenhouse", "lever", "ashby"):
            raise ApiError(422, "provider must be all, remotive, arbeitnow, himalayas, jobicy, remoteok, greenhouse, lever or ashby")
        published = boolean(q, "salary_published")
        debug = boolean(q, "debug")
        max_age_days = integer(q, "max_age_days", 180)
        if not 0 <= max_age_days <= 36500:
            raise ApiError(422, "max_age_days must be between 0 and 36500")
        if provider == "remotive":
            return recent_jobs(run_async(jobs.search(c, job, published, 100)), max_age_days, limit)
        from app import arbeitnow_jobs, remote_job_feeds, ats_job_feeds
        if provider in ("himalayas", "jobicy", "remoteok"):
            return recent_jobs(run_async(remote_job_feeds.search(provider, c, job, published, 100)), max_age_days, limit)
        if provider == "arbeitnow":
            return recent_jobs(run_async(arbeitnow_jobs.search(c, job, published, 100)), max_age_days, limit)
        if provider in ("greenhouse", "lever", "ashby"):
            return recent_jobs(run_async(ats_job_feeds.search(provider, c, job, published, 100, debug=debug)), max_age_days, limit)
        results, failures = [], []
        for name, fn in (("Remotive", jobs.search), ("Arbeitnow", arbeitnow_jobs.search),
                         ("Himalayas", lambda *args: remote_job_feeds.search("himalayas", *args)),
                         ("Jobicy", lambda *args: remote_job_feeds.search("jobicy", *args)),
                         ("Remote OK", lambda *args: remote_job_feeds.search("remoteok", *args)),
                         ("Greenhouse", lambda *args: ats_job_feeds.search("greenhouse", *args)),
                         ("Lever", lambda *args: ats_job_feeds.search("lever", *args)),
                         ("Ashby", lambda *args: ats_job_feeds.search("ashby", *args))):
            try:
                results.append(run_async(fn(c, job, published, 100)))
            except UpstreamUnavailable:
                failures.append(name)
        if not results:
            raise UpstreamUnavailable("All job feeds unavailable")
        from app.job_dedup import merge_jobs
        combined = merge_jobs(listing for result in results for listing in recent_jobs(result, max_age_days, 100)["jobs"])
        return {"status": "available" if combined else "no_results",
                "provider": "EarnWage", "providers": [x["provider"] for x in results],
                "failed_providers": failures, "country": c, "occupation": job,
                "count": len(combined), "returned": min(len(combined), limit),
                "jobs": combined[:limit], "max_age_days": max_age_days,
                "publication_date_note": "Provider-reported dates may be original creation or last update; unknown dates are retained and labelled.",
                "scope": "Eight attributed feeds, including curated employer boards, with conservative geographic matching; not a national vacancy census.",
                "notice": "Each listing links to its attributed provider. Verify eligibility and availability at source."}
    if len(parts) == 4 and parts[:3] == ["v1", "jobs", "remotive"]:
        try:
            job_id = int(parts[3])
        except ValueError:
            raise ApiError(422, "Invalid provider id")
        if job_id <= 0:
            raise ApiError(422, "Invalid provider id")
        detail = run_async(jobs.detail(job_id))
        if detail is None:
            raise ApiError(404, "Job not in latest available Remotive feed")
        return detail
    raise ApiError(404, "Unknown route")


def admin_eurostat(environ, start_response, origin):
    """Import one selected series per authenticated request."""
    from app.eurostat_economy import EUROSTAT_COUNTRIES, SERIES, fetch, save, ensure_tables, read
    from app.country_insights_store import connect as insights_connect
    secret = os.environ.get("EARNWAGE_ADMIN_TOKEN", "")
    supplied = environ.get("HTTP_X_EARNWAGE_ADMIN_TOKEN", "")
    if len(secret) < 32:
        return reply(start_response, {"error": "admin_not_configured"}, 503, "POST", origin)
    if not supplied or not hmac.compare_digest(secret, supplied):
        return reply(start_response, {"error": "unauthorized"}, 401, "POST", origin)
    if environ.get("HTTP_ORIGIN") not in (None, "https://gilpereirapt.github.io"):
        return reply(start_response, {"error": "forbidden_origin"}, 403, "POST", origin)
    try:
        size = int(environ.get("CONTENT_LENGTH", "0") or "0")
        if not 0 < size <= 1024:
            raise ValueError("Invalid request length")
        payload = json.loads(environ["wsgi.input"].read(size).decode("utf-8"))
        code, name = payload.get("country"), payload.get("indicator")
        if code not in EUROSTAT_COUNTRIES or name not in SERIES:
            raise ValueError("Unsupported country or indicator")
    except (ValueError, TypeError, AttributeError, KeyError, UnicodeError):
        return reply(start_response, {"error": "invalid_import_request"}, 422, "POST", origin)
    try:
        observations = fetch(code, SERIES[name])
        status, error_type = ("available" if observations else "empty"), None
    except Exception as exc:
        from urllib.error import HTTPError, URLError
        if not isinstance(exc, (HTTPError, URLError, TimeoutError, ValueError,
                                KeyError, TypeError, OSError)):
            LOG.exception("Unexpected Eurostat import failure")
        observations, status, error_type = [], "failed", type(exc).__name__
    with insights_connect() as db:
        ensure_tables(db)
        save(db, code, name, observations, status, error_type)
        result = read(db, code, name)
    return reply(start_response, {"import_status": status, "observation_count": len(observations),
                                  "indicator": result}, 200, "POST", origin)


def application(environ, start_response):
    """WSGI entry for Passenger; never display tracebacks or server paths."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    origin = environ.get("HTTP_ORIGIN")
    if origin != "https://gilpereirapt.github.io":
        origin = None
    path = environ.get("PATH_INFO", "/")
    normalized = path.rstrip("/")
    data_manager_actions = {
        "/v1/admin/data-manager/status": "status",
        "/v1/admin/data-manager/backup": "backup",
        "/v1/admin/data-manager/import": "import",
        "/v1/admin/data-manager/deploy": "deploy",
        "/v1/admin/data-manager/bulk-preview": "bulk_preview",
        "/v1/admin/data-manager/bulk-publish": "bulk_publish",
        "/v1/admin/data-manager/bulk-rollback": "bulk_rollback",
        "/v1/admin/data-manager/salary-inventory": "salary_inventory",
    }
    if normalized in data_manager_actions and method == "OPTIONS":
        if origin != "https://gilpereirapt.github.io":
            return reply(start_response, {"error": "forbidden_origin"}, 403, "OPTIONS", origin)
        start_response("204 No Content", [
            ("Access-Control-Allow-Origin", origin),
            ("Access-Control-Allow-Methods", "POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, X-EarnWage-Admin-Token"),
            ("Access-Control-Max-Age", "600"),
            ("Vary", "Origin"),
            ("Cache-Control", "no-store"),
            ("Content-Length", "0")])
        return []
    if normalized in data_manager_actions and method not in ("POST", "OPTIONS"):
        return reply(start_response, {"error": "method_not_allowed"}, 405, method, origin)
    if normalized in data_manager_actions and method == "POST":
        from app.data_manager import handle
        return handle(environ, start_response, origin,
                      data_manager_actions[normalized], reply)
    if path.rstrip("/") == "/v1/admin/eurostat/import" and method == "OPTIONS":
        if origin != "https://gilpereirapt.github.io":
            return reply(start_response, {"error": "forbidden_origin"}, 403, "OPTIONS", origin)
        start_response("204 No Content", [
            ("Access-Control-Allow-Origin", origin),
            ("Access-Control-Allow-Methods", "POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, X-EarnWage-Admin-Token"),
            ("Access-Control-Max-Age", "600"),
            ("Vary", "Origin"),
            ("Cache-Control", "no-store"),
            ("Content-Length", "0")])
        return []
    if path.rstrip("/") == "/v1/admin/eurostat/import" and method == "POST":
        return admin_eurostat(environ, start_response, origin)
    if method not in ("GET", "HEAD"):
        return reply(start_response, {"detail": "Only GET and HEAD are supported"},
                     405, method, origin)
    if len(path) > 2048:
        return reply(start_response, {"detail": "Invalid request path"}, 422, method, origin)
    try:
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True,
                         max_num_fields=30)
        if any(len(str(value)) > 1024 for values in query.values() for value in values):
            raise ApiError(422, "Query parameter too long")
        initialize()
        data = dispatch(path.rstrip("/") or "/", query)
        return reply(start_response, data, method=method, origin=origin)
    except ApiError as exc:
        return reply(start_response, {"detail": exc.detail}, exc.code, method, origin)
    except LookupError as exc:
        return reply(start_response, {"detail": str(exc)}, 404, method, origin)
    except ValueError as exc:
        return reply(start_response, {"detail": str(exc)}, 422, method)
    except UpstreamUnavailable:
        return reply(start_response, {"error": "upstream_unavailable"}, 503, method, origin)
    except Exception:
        LOG.exception("EarnWage WSGI request failed: %s", path)
        return reply(start_response, {"error": "internal_server_error"}, 500, method, origin)

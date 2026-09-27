"""Native WSGI HTTP adapter for CloudLinux Passenger/LiteSpeed.

Does not import FastAPI or a2wsgi. Reuses EarnWage's validated business modules.
FastAPI app.main remains for local ASGI / existing API tests.
"""
import asyncio
import json
import logging
import unicodedata
import threading
from pathlib import Path
from urllib.parse import parse_qs

from app.catalog import COUNTRY_MAP, OCCUPATIONS, SUPPORTED_LANGUAGES
from app import earnwage_queries as ew
from app import north_america as na
from app import jobs
from app.client_config import configuration, region_configuration
from app.ilostat_import import (
    TOC, earnings_datasets, availability, load_snapshot, catalogue_rows,
)
from app.providers import UpstreamUnavailable, exchange_rate, inflation_series
from app.store import connect
from app.tax_components import components as tax_components

VERSION = "0.5.6"
ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger("earnwage.wsgi")
JOBS = {job["id"]: job for job in OCCUPATIONS}
INITIALIZED = False
INIT_LOCK = threading.Lock()
HTTP_STATUS = {
    200: "200 OK", 400: "400 Bad Request", 404: "404 Not Found",
    405: "405 Method Not Allowed", 413: "413 Content Too Large",
    422: "422 Unprocessable Entity", 503: "503 Service Unavailable",
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
        "remotive_jobs": {"url": "https://remotive.com/remote-jobs/api",
            "role": "Remote-only attributed job listings", "status": "integrated"},
        "ilostat": {"url": TOC, "role": "Official occupation earnings",
            "status": "offline importer; source availability not guaranteed"},
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
        return {"status": "ok", "version": VERSION,
                "service": "EarnWage API",
                "runtime": "native_wsgi"} if path == "/v1/health" else {
                    "service": "EarnWage API", "version": VERSION,
                    "health": "/v1/health", "documentation": "See README.md in GitHub"}
    if path == "/v1/app-config":
        return configuration()
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
        for cell in result["cells"]:
            period = observations.get((cell["country"], cell["occupation"]))
            if period is not None:
                cell.update(status="available", latest_period=period,
                            source_family="north_america_official_wages")
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
    if path == "/v1/jobs":
        c, job = country(one(q, "country")), occupation(one(q, "occupation"))
        limit = integer(q, "limit", 20)
        if not 1 <= limit <= 100:
            raise ApiError(422, "limit must be between 1 and 100")
        return run_async(jobs.search(c, job, boolean(q, "salary_published"), limit))
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


def application(environ, start_response):
    """WSGI entry for Passenger; never display tracebacks or server paths."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    origin = environ.get("HTTP_ORIGIN")
    if origin != "https://gilpereirapt.github.io":
        origin = None
    if method not in ("GET", "HEAD"):
        return reply(start_response, {"detail": "Only GET and HEAD are supported"},
                     405, method, origin)
    path = environ.get("PATH_INFO", "/")
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

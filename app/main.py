"""HTTP contract for Android and web clients."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.catalog import COUNTRY_MAP, OCCUPATIONS, SUPPORTED_LANGUAGES
from app import jobs as job_provider
from app import north_america as na_wages
from app.client_config import configuration as earnwage_configuration, region_configuration
from app import earnwage_queries as ew_queries
from app.tax_components import components as tax_components
from app.providers import UpstreamUnavailable, exchange_rate, inflation_series
from app.store import connect
from app.ilostat_import import salary, availability, earnings_datasets, TOC, download, load_snapshot, catalogue_rows
import csv
import io
import unicodedata

@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect():
        pass
    from pathlib import Path
    load_snapshot(Path(__file__).resolve().parent.parent / "data" / "salaries_snapshot.json")
    na_wages.load_snapshot(Path(__file__).resolve().parent.parent / "data" / "north_america_wages.json")
    yield

app = FastAPI(
    title="EarnWage — Global Purchasing Power API",
    version="0.5.2",
    description="Free official economic data, normalized with provenance. No fabricated salaries or capital prices.",
    lifespan=lifespan,
)

@app.exception_handler(UpstreamUnavailable)
async def upstream_error(request, exc):
    return JSONResponse(status_code=503, content={"error": "upstream_unavailable", "detail": str(exc)})

@app.get("/v1/health")
def health():
    return {"status": "ok", "version": app.version}

@app.get("/v1/app-config")
def app_config():
    """EarnWage identity and client UI capabilities; no client-specific secret."""
    return earnwage_configuration()


@app.get("/v1/regions/{country}")
def region_options(country: str):
    """Optional state/province selector for supported regions only."""
    result = region_configuration(country)
    if result is None:
        raise HTTPException(404, "Unknown country")
    return result


@app.get("/v1/countries")
def countries():
    return {"countries": list(COUNTRY_MAP.values()), "count": len(COUNTRY_MAP)}

@app.get("/v1/countries/{code}")
def country(code: str):
    item = COUNTRY_MAP.get(code.upper())
    if not item:
        raise HTTPException(404, "Unknown country")
    return item

@app.get("/v1/languages")
def languages():
    return {"languages": [{"code": k, "label": v} for k, v in SUPPORTED_LANGUAGES.items()],
            "default": "en", "portuguese_locale": "pt",
            "note": "Occupation labels are localized in all seven supported languages; other interface text may require client localization."}

def _search_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char)).strip()


@app.get("/v1/occupations")
def occupations(lang: str = Query("en", pattern="^[a-z]{2}(-[A-Za-z]{2})?$"),
                q: str | None = Query(default=None, max_length=100)):
    base = lang.split("-")[0].lower()
    if base not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, "Unsupported interface language")
    term = _search_key(q or "")
    items = []
    for item in OCCUPATIONS:
        terms = [item["id"], *item["translations"].values(),
                 *(alias for group in item.get("aliases", {}).values() for alias in group)]
        if term and not any(term in _search_key(value) for value in terms):
            continue
        items.append({"id": item["id"], "isco08": item["isco08"],
                      "label": item["translations"][base],
                      "translations": item["translations"],
                      "aliases": item.get("aliases", {})})
    return {"language": base, "fallback": "en", "count": len(items), "occupations": items}

@app.get("/v1/inflation/{code}")
async def inflation(code: str):
    item = COUNTRY_MAP.get(code.upper())
    if not item:
        raise HTTPException(404, "Unknown country")
    if item["inflation_provider"] != "eurostat":
        return {"country": item["code"], "status": "unavailable",
                "reason": "No validated free national importer in v0.1.0"}
    return {"status": "available", **await inflation_series(item["code"])}

@app.get("/v1/exchange-rates/{currency}")
async def fx(currency: str):
    code = currency.upper()
    if len(code) != 3 or not code.isalpha():
        raise HTTPException(422, "Invalid ISO currency")
    result = await exchange_rate(code)
    if result is None:
        return {"currency": code, "status": "unavailable",
                "reason": "No ECB reference series for this currency"}
    return {"status": "available", **result}

@app.get("/v1/compare")
async def compare(country_a: str, country_b: str, occupation: str | None = None):
    a, b = country_a.upper(), country_b.upper()
    if a not in COUNTRY_MAP or b not in COUNTRY_MAP:
        raise HTTPException(404, "Unknown country")
    if occupation and occupation not in {x["id"] for x in OCCUPATIONS}:
        raise HTTPException(422, "Unknown occupation")
    import asyncio
    async def side(code):
        item = COUNTRY_MAP[code].copy()
        item["salary"] = (
            na_wages.wages(code, occupation) if code in ("US", "CA") else salary(code, occupation)
        ) if occupation else {"status": "unavailable", "reason": "Select an occupation"}
        item["tax"] = {"status": "unavailable", "reason": "Country-specific model not validated"}
        item["capital_cost_of_living"] = {"status": "unavailable", "reason": "No verified capital-level series"}
        if item["inflation_provider"] == "eurostat":
            item["inflation"] = {"status": "available", **await inflation_series(code)}
        else:
            item["inflation"] = {"status": "unavailable", "reason": "Validated importer pending"}
        return item
    first, second = await asyncio.gather(side(a), side(b))
    return {"version": app.version, "country_a": first, "country_b": second,
            "occupation": occupation, "comparison_note": "National inflation is NOT city cost of living; no fabricated profession wages or net salary."}

@app.get("/v1/sources")
def sources():
    return {
        "irs_2026_federal_tax": {"url": "https://www.irs.gov/irb/2025-45_IRB",
                                "role": "2026 US federal single tax brackets and standard deduction",
                                "status": "partial illustration implemented"},
        "cra_2026_cpp_ei": {"url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032oc-jan/t4032oc-january-general-information.html",
                            "role": "2026 CPP, CPP2, and EI employee contribution rates outside Quebec",
                            "status": "partial illustration implemented"},
        "canada_job_bank_wages": {
            "url": na_wages.CANADA_URL,
            "role": "Canada national occupational hourly/annual median and mean, as published",
            "status": "official national wages imported for mapped NOC occupations",
        },
        "us_bls_oews": {
            "url": na_wages.BLS_TABLE,
            "role": "US national detailed occupation wages in BLS May 2025 workbook",
            "status": "May 2025 official national Table 1 nine mean wages imported; full XLSX importer available",
        },
        "remotive_jobs": {
            "url": "https://remotive.com/remote-jobs/api",
            "role": "Attributed remote job listings only, not national vacancy coverage",
            "status": "integrated",
            "terms_url": "https://remotive.com/remote-jobs/api",
        },
        "ilostat": {"url": "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator/",
                    "role": "ISCO-08 occupation-specific annual employee earnings",
                    "status": "offline importer implemented; import required"},
        "eurostat_hicp": {"url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr",
                          "role": "monthly harmonized national inflation", "status": "implemented"},
        "ecb_exr": {"url": "https://data-api.ecb.europa.eu/service/data/EXR",
                    "role": "reference exchange rates", "status": "implemented"},
        "esco": {"url": "https://ec.europa.eu/esco/api/", "role": "profession translations and identifiers",
                 "status": "planned; current labels are curated, not ESCO-linked"},
        "oecd": {"url": "https://sdmx.oecd.org/public/rest/v1/",
                 "role": "national wages and taxing wages", "status": "planned"},
    }

@app.get("/v1/salaries/availability/matrix")
def salary_availability_matrix(lang: str = Query("en", pattern="^[a-z]{2}(-[A-Za-z]{2})?$")):
    base = lang.split("-")[0].lower()
    if base not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, "Unsupported interface language")
    labels = {item["id"]: item["translations"][base] for item in OCCUPATIONS}
    result = availability()
    result["language"] = base
    for cell in result["cells"]:
        cell["occupation_label"] = labels[cell["occupation"]]
    na = na_wages.observed_coverage()
    for cell in result["cells"]:
        key = (cell["country"], cell["occupation"])
        if key in na:
            cell.update({"status": "available", "latest_period": na[key],
                         "source_family": "north_america_official_wages"})
    result["available_cells"] = sum(x["status"] == "available" for x in result["cells"])
    return result


@app.get("/v1/salaries/{code}/{occupation}")
def occupation_salary(code: str, occupation: str):
    country = code.upper()
    if country not in COUNTRY_MAP:
        raise HTTPException(404, "Unknown country")
    if occupation not in {x["id"] for x in OCCUPATIONS}:
        raise HTTPException(422, "Unknown occupation")
    return na_wages.wages(country, occupation) if country in ("US", "CA") else salary(country, occupation)


@app.get("/v1/ilostat/datasets")
def ilostat_datasets():
    """Read-only official catalogue. Large imports are CLI-only, never HTTP."""
    from app.providers import UpstreamUnavailable
    try:
        datasets = earnings_datasets(catalogue_rows())
    except Exception as exc:
        raise UpstreamUnavailable("ILOSTAT catalogue unavailable") from exc
    return {"source_url": TOC, "datasets": datasets}

@app.get("/v1/jobs")
async def job_search(country: str, occupation: str,
                     salary_published: bool = False,
                     limit: int = Query(default=20, ge=1, le=100)):
    destination = country.upper()
    if destination not in COUNTRY_MAP:
        raise HTTPException(404, "Unknown country")
    if occupation not in {x["id"] for x in OCCUPATIONS}:
        raise HTTPException(422, "Unknown occupation")
    return await job_provider.search(destination, occupation, salary_published, limit)


@app.get("/v1/jobs/remotive/{job_id}")
async def job_detail(job_id: int):
    if job_id <= 0:
        raise HTTPException(422, "Invalid provider id")
    record = await job_provider.detail(job_id)
    if record is None:
        raise HTTPException(404, "Job not in latest available Remotive feed")
    return record

@app.get("/v1/wages/{country}/{occupation}")
def north_america_wages(country: str, occupation: str):
    code = country.upper()
    if code not in COUNTRY_MAP:
        raise HTTPException(404, "Unknown country")
    if occupation not in {x["id"] for x in OCCUPATIONS}:
        raise HTTPException(422, "Unknown occupation")
    return na_wages.wages(code, occupation)

@app.get("/v1/tax-components/{country}")
def tax_components_endpoint(
    country: str,
    annual_gross: float = Query(..., gt=0, le=100000000),
    tax_year: int = 2026,
    filing_status: str = "single",
    province: str | None = None,
):
    """Partial source-backed 2026 components, deliberately no take-home pay."""
    code = country.upper()
    if code not in COUNTRY_MAP:
        raise HTTPException(404, "Unknown country")
    if code not in ("US", "CA"):
        return tax_components(code, annual_gross, tax_year=tax_year)
    try:
        return tax_components(code, annual_gross, tax_year=tax_year,
                              filing_status=filing_status,
                              province=province.upper() if province else None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/earnwage/coverage")
def earnwage_coverage():
    """Real imported wage coverage; safe to show on an Android home screen."""
    return ew_queries.coverage()


@app.get("/v1/earnwage/overview")
def earnwage_overview(
    country: str,
    occupation: str,
    region: str | None = None,
    annual_gross: float | None = Query(default=None, gt=0, le=100000000),
    tax_year: int = 2026,
):
    """One screen-ready place/occupation record, no live external requests."""
    try:
        return ew_queries.overview(country, occupation, region, annual_gross, tax_year)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/earnwage/compare")
def earnwage_compare(
    country_a: str,
    country_b: str,
    occupation: str,
    region_a: str | None = None,
    region_b: str | None = None,
    annual_gross_a: float | None = Query(default=None, gt=0, le=100000000),
    annual_gross_b: float | None = Query(default=None, gt=0, le=100000000),
    tax_year: int = 2026,
):
    """Side-by-side verified national wages, never a fabricated PPP winner."""
    try:
        return ew_queries.compare(country_a, country_b, occupation, region_a, region_b,
                                  annual_gross_a, annual_gross_b, tax_year)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

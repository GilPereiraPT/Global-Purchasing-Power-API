# Global Purchasing Power API

Free-source international economic data backend for Android and web. **v0.3.1 is a first integration, not a completed wage or tax calculator.**

## Current scope

- 14 country/capital/currency catalogue entries (including India, Brazil and Pakistan).
- 40 curated occupations with English and Portuguese labels; validated exact ISCO-08 mappings for selected occupations. Missing mappings remain null.
- Live Eurostat monthly national HICP (dataset `prc_hicp_minr`) for supported European geographies.
- Live ECB daily reference exchange rates where ECB publishes the currency.
- SQLite response cache, explicit source URLs, and machine-readable unavailable results.
- ILOSTAT offline importer: official annual occupation/monthly-earnings CSV.GZ; accepts only sex-total, exact 4-digit ISCO-08 and explicitly local-currency observations. Source and year retained.\n- Country comparison now includes imported ILOSTAT occupation wage, if present. Taxes and capital costs remain explicitly unavailable.

**Important:** a national wage is not a capital wage; a price-level index is not a city spending basket; a statistical average tax burden is not personal income-tax liability. Never replace missing observations with fabricated figures. No paid API dependencies.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger.

## Quick requests

```text
GET /v1/health
GET /v1/countries
GET /v1/occupations?lang=pt
GET /v1/inflation/PT
GET /v1/inflation/IN
GET /v1/exchange-rates/USD
GET /v1/compare?country_a=PT&country_b=DE&occupation=accountant
GET /v1/sources
```

Use `GPP_CACHE_DB=/absolute/writable/path/cache.sqlite3` on cPanel. The default `/tmp/gpp_api_cache.sqlite3` is suitable for development but may not persist across hosting restarts.

On a cPanel deployment that supports Python Passenger WSGI applications, point the app at `passenger_wsgi.py`. It uses the included `a2wsgi` adapter to wrap FastAPI's ASGI interface. Verify the host's Python version, startup path and Passenger process configuration before production use.

Run tests: `pytest -q`. GitHub Actions executes the local test suite on push and pull requests.

## Source attribution

Eurostat: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr

ECB: https://data-api.ecb.europa.eu/service/data/EXR

Check reuse terms for each additional dataset before commercial release.

## ILOSTAT import (server administrator)

Official catalogue: https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator/table_of_contents_en.csv

```bash
python -m app.ilostat_import --list
python -m app.ilostat_import --dataset VERIFIED_ANNUAL_DATASET_ID
```

Choose the annual dataset whose exact catalogue label refers to **average monthly earnings of employees by sex and occupation**, denominated in local currency, then import it. The importer checks the official catalogue and refuses unlisted IDs, compressed archives over 35 MiB and inflated files over 180 MiB. Downloads can be slow; never execute imports on a public HTTP request.

```text
GET /v1/ilostat/datasets
GET /v1/salaries/PT/accountant
GET /v1/salaries/IN/nurse
GET /v1/salaries/availability/matrix
```

The matrix has 40 × 14 = 560 cells. Before importing data, all cells are unavailable. Salary records are only emitted where official source rows were imported. A single exact occupation row is required for the latest year; multiple competing rows are marked ambiguous rather than silently averaged.

**Coverage caveat:** the catalogue may contain ILOSTAT earnings data but not a specific country's exact ISCO-08 occupation, year, or currency. No inference from country-wide averages to the capital is allowed. The app should display `status: unavailable` instead of inventing numbers. Check source terms and attribution before commercial release.

## Publish actual wages from the free ILOSTAT source

The ILOSTAT import is **opt-in** until a complete source run has been validated. An attempted live import on 2026-09-26 received HTTP 404 from the officially documented bulk catalogue URL. Therefore no real salary snapshot has been committed; the other API endpoints and tests remain usable. The REST endpoint was reachable but did not provide verified importable observations in this test. Do not claim live salary coverage until a source import passes.
Navigate to **Actions → Refresh official ILOSTAT salaries → Run workflow**.
The default candidate is `EAR_EMTA_SEX_OCU_CUR_NB_A`, but the job checks its existence
and label against ILOSTAT's live official catalogue before downloading anything.
If the file, column schema or units do not match, the job fails without publishing a
salary snapshot.

When successful, it commits `data/salaries_snapshot.json` containing real observations
with source, year, ISO currency, and exact ISCO-08 classification. The API loads that
snapshot on startup into SQLite; no SQLite database is committed to the repository.
Only wages with a **validated exact occupation code** are shown. Other job/country
combinations remain unavailable.

The ILOSTAT table may not provide all 40 professions or all 14 countries;
the availability matrix reports the actual imported coverage, not an estimate.

## Jobs module v0.3.1 — attributed remote vacancies

The first jobs provider is **Remotive**: https://remotive.com/remote-jobs/api .
Its public API permits developers to share listings with a visible **Remotive**
credit and a direct link back to the listing. Do not gate listings behind sign-up,
and do not syndicate them to third-party job boards. The feed is cached for six
hours to respect the provider's recommendation of at most four requests per day.

```text
GET /v1/jobs?country=DE&occupation=software_developer
GET /v1/jobs?country=BR&occupation=accountant&salary_published=true
GET /v1/jobs/remotive/12345
```

The first route returns only title matches from the Remotive remote feed whose
candidate eligibility is marked worldwide or mentions the requested country.
A worldwide-eligible remote job is **not** an employer located in that country.
A job matching no listings returns `no_results`, NOT a false claim that the
country has no openings. Broad occupation `manager` returns `unavailable`
because title matching is too vague. Listings may expire between feed checks.

Published free-text salary is exposed as `salary_text` without inventing a
numeric amount, annualization, currency or net salary. Salary-to-purchasing-power
comparison requires a verified structured offer or user-entered gross salary and
a separately validated country tax engine; it is NOT implemented here.

All fourteen countries, including India, Brazil, Pakistan, USA and Canada, remain
available as destination *eligibility filters*, not claims that local in-person
job coverage exists. The provider is Remote-only. Other sources require explicit
rights for commercial reuse; no scraping or unlicensed redistribution.

## Version 0.3.1 — North America and interface languages

The initial country catalogue now includes **United States (US, Washington D.C., USD)**
and **Canada (CA, Ottawa, CAD)**, for fourteen countries and 560 occupation-country cells.
No US or Canada inflation or wage series are invented: until a compatible free
importer and real observations exist, their values are returned as unavailable.
The Remotive remote eligibility search recognizes USA/United States and Canada.

The language catalogue contains exactly seven single interface locales: `en`,
`pt`, `es`, `de`, `fr`, `it`, `nl`. Portugal and Brazil use the **same**
`pt` interface, India/Pakistan/USA use `en`, and Canada supports `en`/`fr`.
Occupation labels are currently translated only into English and Portuguese;
other selected languages fall back to English pending actual translations.
`GET /v1/languages` exposes the planned interface locales.

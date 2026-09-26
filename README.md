# Global Purchasing Power API

Free-source international economic data backend for Android and web. **v0.2.0 is a first integration, not a completed wage or tax calculator.**

## Current scope

- 12 country/capital/currency catalogue entries (including India, Brazil and Pakistan).
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

The matrix has 40 × 12 = 480 cells. Before importing data, all cells are unavailable. Salary records are only emitted where official source rows were imported. A single exact occupation row is required for the latest year; multiple competing rows are marked ambiguous rather than silently averaged.

**Coverage caveat:** the catalogue may contain ILOSTAT earnings data but not a specific country's exact ISCO-08 occupation, year, or currency. No inference from country-wide averages to the capital is allowed. The app should display `status: unavailable` instead of inventing numbers. Check source terms and attribution before commercial release.

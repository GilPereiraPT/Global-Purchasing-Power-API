# Global Purchasing Power API

Free-source international economic data backend for Android and web. **v0.1.0 is a first integration, not a completed wage or tax calculator.**

## Current scope

- 12 country/capital/currency catalogue entries (including India, Brazil and Pakistan).
- 30 curated occupations with English and Portuguese labels; additional languages and ESCO codes pending.
- Live Eurostat monthly national HICP (dataset `prc_hicp_minr`) for supported European geographies.
- Live ECB daily reference exchange rates where ECB publishes the currency.
- SQLite response cache, explicit source URLs, and machine-readable unavailable results.
- Country comparison shape with salary, taxes and capital costs **explicitly unavailable** until verifiable free sources are integrated.

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

Use `GPP_CACHE_DB=/absolute/writable/path/cache.sqlite3` on cPanel. The default `/tmp/gpp_api_cache.sqlite3` is suitable for development but may not persist across hosting restarts. Deploy `passenger_wsgi.py` with a cPanel Python environment configured for ASGI compatibility: vanilla Passenger WSGI does **not** directly serve FastAPI ASGI; run Uvicorn behind a proxy or use a tested ASGI-to-WSGI adapter. Do not assume the file alone makes FastAPI work under Passenger.

Run tests: `pytest -q`.

## Source attribution

Eurostat: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr

ECB: https://data-api.ecb.europa.eu/service/data/EXR

Check reuse terms for each additional dataset before commercial release.

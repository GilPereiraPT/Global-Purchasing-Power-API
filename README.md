# EarnWage — Global Purchasing Power API

Free-source international economic data backend for Android and web. **v0.5.3 is an integration-stage backend, not a complete net salary or purchasing-power calculator.**

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

On cPanel/CloudLinux Passenger, point the app at `passenger_wsgi.py`, entry point `application`. This deployment now uses **native WSGI** (`app/native_wsgi.py`) rather than an ASGI adapter: FastAPI/`a2wsgi` failed to answer HTTP requests on the actual host even though imports passed. FastAPI `app.main:app` is preserved for ASGI-capable hosts and local tests. Verify the host's Python version, startup path and Passenger process configuration.

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

## Jobs module v0.4.2 — attributed remote vacancies

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

## 0.4.0 — North America wage observations (no guesses)

Canada source: [Job Bank 2025 Wages open data](https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116), Open Government Licence Canada. Its official CSV has NOC unit group, national/provincial/region, minimum/median/mean/maximum, reference period, and annual-wage flag. This importer currently supports a **small explicitly mapped subset of occupations**, always restricts to `prov=NAT` and `ER_Code_Code_RE=ER00`, and keeps published wage units intact (`CAD/hour` or `CAD/year`). It does not claim Ottawa wages from national rows.

US source: [BLS May 2025 OEWS](https://www.bls.gov/oes/tables.htm), an official free XLSX workbook. The BLS host may return 403 to automated clients. Download the official **national** XLSX manually and import with `python -m app.north_america --us-xlsx FILE --year 2025`. Only selected confirmed SOC detailed codes and national `AREA=99` rows are accepted; annual **mean** and median are not merged.

```bash
python -m app.north_america --canada
python -m app.north_america --export
# The web server automatically loads data/north_america_wages.json at startup
```

```text
GET /v1/wages/CA/nurse
GET /v1/wages/US/software_developer
```

The US and Canada providers never synthesize annual or monthly salaries from hourly rates. Values are published with their **unit, measure, occupation code, published year, reference period and original source**. No values are shown until successfully imported. The Canadian import job runs on workflow dispatch; successful validated snapshot changes are versioned in GitHub.

## Verified Canadian import — updated 2026-09-26

GitHub Actions imported **56 actual official national wage observations**
for **28 mapped NOC occupations** from the Canadian 2025 Job Bank file and committed
`data/north_america_wages.json`. Mean and median are stored independently: 28 × 2
observations. The statistical reference period is generally **2023–2024**, but
dentists use **2021**. The publication is dated **2025**, so do not portray
these as observed 2026 earnings.

For the other **12** catalogue professions in Canada the response is
`unavailable`. US wages for nine SOC occupations have since been imported from official BLS national Table 1; the other 31 remain unavailable. National wages must not be relabeled as Ottawa or Washington wages.

View the committed, attributable observations:
https://github.com/GilPereiraPT/Global-Purchasing-Power-API/blob/main/data/north_america_wages.json

## v0.4.2 — broader Canada and unified salary coverage

An official GitHub Actions source audit identified **28 NOC 2021 unit group mappings** to the 40 curated professions (up from 4). The importer checks the *original English occupation title* for each NOC code, national area and source wage units. **A NOC group is not always identical to the shorter translated occupation label**: each observation exposes the original NOC group title so users can inspect scope. Some professions still have no defensible NOC equivalence and remain unavailable.

Both `GET /v1/salaries/CA/{occupation}` and `GET /v1/wages/CA/{occupation}` return the same North American observations, and the 560-cell `GET /v1/salaries/availability/matrix` now includes real imported Canadian data as available. USA is available for nine reviewed BLS occupation rows; 31 occupations remain unavailable. This fixes a prior discrepancy where Canadian salaries existed but the general salary matrix incorrectly showed unavailable.

## v0.4.2 — official US May 2025 national wages now included

The BLS 2025 OEWS national spreadsheet is blocked to automated GitHub runners
(HTTP 403), but BLS publishes the same **annual mean wages** in its
[official national 2025 press release Table 1](https://www.bls.gov/news.release/ocwage.t01.htm).
Nine occupation rows were verified against that original public federal table
and checked into `data/bls_2025_release_reviewed.csv`. The import workflow
preserves the existing Canadian data, adds nine original USD/year national
**mean** observations, and commits the complete combined snapshot. It does
not invent medians from BLS Table 1's median **hourly** column, or claim
that this reviewed subset is the full BLS XLSX. Source data reference
**May 2025**, and the release was published **15 May 2026**.

```text
GET /v1/salaries/US/nurse
GET /v1/wages/US/software_developer
GET /v1/salaries/availability/matrix
```

Coverage: **9 of 40** US occupations; **28 of 40** Canadian occupations;
`560` total potential country/occupation cells. US/Canadian records = **65**,
covering **37** distinct country/occupation cells. Other combinations
remain unavailable. A Canadian reimport loads the existing combined
snapshot first, so its update cannot silently erase American wages.

## v0.5.0 — strictly partial 2026 tax components, not net pay

The new `GET /v1/tax-components/{country}` accepts an **explicit user
annual gross wage**, never silently annualizes Job Bank hourly pay and never
pretends that May 2025 BLS wages were observed in tax year 2026.

```text
GET /v1/tax-components/US?annual_gross=101420&tax_year=2026
GET /v1/tax-components/CA?annual_gross=100000&province=ON&tax_year=2026
```

**US:** Standard *single* employee only: official 2026 federal marginal
brackets, USD 16,100 standard deduction, employee Social Security (6.2% up
to USD 184,500), Medicare (1.45%), and additional Medicare (0.9% on wages
above USD 200,000). The income-tax figure is **before credits**. Missing:
state/local taxes, credits, itemized and special deductions, health/pension
premiums, complex wage circumstances. Filing statuses besides single are
rejected rather than silently modeled with single thresholds.

Sources:
- https://www.irs.gov/irb/2025-45_IRB
- https://www.irs.gov/taxtopics/tc751
- https://www.irs.gov/taxtopics/tc560

**Canada:** 2026 employee CPP base (4.95%), first additional CPP (1%),
CPP2 (4% above CAD 74,600 through CAD 85,000) and EI (1.63% up to
CAD 68,900), for a typical CPP/EI-covered adult employee **outside Quebec**.
A supported non-Quebec province must be supplied. Federal and provincial
income tax are NOT calculated. The Quebec regime and special occupations
need independent validation.

Source: https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032oc-jan/t4032oc-january-general-information.html

Both return `status: partial_estimate`, `net_income: null`, itemized
components, excluded items and source URLs. **Do not label a subtotal of these
items "net salary", "take-home pay", "disposable income", or purchasing power.**
The 2026 tax-rule year is distinct from each source occupation wage's own
statistical reference period.

## v0.5.1 — EarnWage public identity and simple country/region UX

The public application is **EarnWage**, subtitle **Salary & Cost of Living**,
tagline **Your salary. Your world.** The technical project and current
repository remain `Global-Purchasing-Power-API`, without breaking endpoint
paths, SQLite snapshot schemas or the Collexall service. No live deployment,
DNS change, Android bundle rename or trademark/domain registration is implied.

```text
GET /v1/app-config
GET /v1/regions/US
GET /v1/regions/CA
GET /v1/regions/PT
```

`/v1/app-config` exposes brand strings, 14 country codes, seven intended
interface languages (a single `pt` for Portugal and Brazil), a default `en`,
and a **conditional** region selector. Only the US and Canada show optional
state/province choices. All fifty US states and thirteen Canadian provinces
and territories are exposed as *selection options*, **not** as claims of
available state/provincial tax calculation.

For US and Canada, the API returns a warning that local tax rules may differ.
Québec is flagged as requiring its distinct payroll regime. A partial
federal/national estimate remains partial after selecting a region. Other
countries do not show an additional region field by default. This is a client
configuration contract, ready for the later Android/web interface.

## v0.5.2 — EarnWage app-ready, consolidated read-only queries

Development can continue through GitHub without access to the production
cPanel server. These endpoints use the committed snapshots and local SQLite
only; they do not trigger live Remotive/Eurostat/ECB calls as the user changes
form fields.

```http
GET /v1/earnwage/coverage
GET /v1/earnwage/overview?country=US&occupation=nurse
GET /v1/earnwage/overview?country=US&occupation=nurse&region=NY&annual_gross=101420
GET /v1/earnwage/overview?country=CA&occupation=nurse&region=ON
GET /v1/earnwage/compare?country_a=US&country_b=CA&occupation=nurse&region_a=NY&region_b=ON
```

`/v1/earnwage/coverage` counts actual imported, available wage
country/occupation pairs. With the current reviewed snapshots the status is
**37 of 560** pairs: 9 US, 28 CA, none elsewhere. This number changes with
actual validated imports, never with unsupported projections.

`/v1/earnwage/overview` returns occupation name, national wage with original
measure, unit and reference period, conditional region-selector metadata,
optional independently-entered **annual** gross tax scenario, limitations,
and explicitly unavailable capital expenses and net purchasing power.
A salary from an official occupation table is **never** treated as a personal
salary; hourly wages are **never** silently annualized. For US tax scenarios,
even selecting a state does not claim that state tax is included. For Canada,
selecting a province is optional for exploring wages but needed for the
partial CPP/EI scenario; Québec returns unavailable fiscal components rather
than using inappropriate non-Québec payroll rates.

`/v1/earnwage/compare` returns the two sourced records **side by side**,
without comparing different currencies, mixing annual/hourly wage units,
or ranking countries by a fabricated "winner". Each side accepts an optional
own gross annual salary, so two real-world offers can be examined separately
once validated tax engines are available.

Existing `/v1/compare`, `/v1/salaries`, `/v1/jobs` and all other v1 API
routes remain supported. There is no server deployment or DNS action in this
commit.

## v0.5.3 — CloudLinux native WSGI deployment (Collexall pattern)

The actual cPanel host successfully served a pure WSGI test, while minimal
FastAPI + a2wsgi requests hung without HTTP response. The production
`passenger_wsgi.py` therefore now **imports a native WSGI callable**, not
`ASGIMiddleware`. The API's salary, country, occupation, region, tax,
source, coverage, overview and compare logic reuse the existing source-
validated Python modules. The legacy FastAPI app is kept independently for
local/other ASGI use. Both entrypoints have tests; changing WSGI adapter
does not change the real wage snapshots.

Upload/copy these updated files from the repository to the **existing**
`/home3/policli1/api-earnwage` application:

```text
passenger_wsgi.py
app/native_wsgi.py
```

Do not paste the Collexall code into EarnWage. Do not overwrite cPanel's
`.htaccess`. Python 3.12, the environment and dependencies were already
verified on the host. Restart only the EarnWage Python app and visit
`https://earnwage-api.policlinicosdesantoandre.com/v1/health`.
Expected: `status=ok`, `version=0.5.3`, `runtime=native_wsgi`.

The WSGI entrypoint loads checked-in wage snapshots at the first request
per process. It uses the existing cPanel environment for SQLite/cache.
Do not publish directory indexing, `.py` sources, SQLite files or internal
`data/` as static HTTP resources. Configure a separate non-public application
root/public document root where supported; ask hosting support when necessary.
Do not assume passing GitHub Actions means the public domain is deployed.
`/docs` is a FastAPI-only development route and is not exposed by native
WSGI: use the README endpoint list.

Native WSGI external-data routes call the existing async providers through
a per-request event loop. Server-specific live HTTP requests still require
individual smoke tests after deployment; local unit tests prove routing and
payload format, not external provider availability.

## Eurostat economic reference series (cron-only, no API key)

The Eurostat module imports three independently labelled observations for PT, ES,
DE, FR, IE, NL, IT, GB and CH **where the official series actually contains
data**. Availability is not assumed from country membership.

- `hicp_annual_change_monthly`: `prc_hicp_minr`, all-items CP00,
  annual percentage change for each month; NOT the price index itself.
- `household_price_level_eu27`: `prc_ppp_ind`, household final
  consumption E011, EU27_2020=100. This is the historical COICOP 1999
  series; do not splice with `prc_ppp_ind_1` without a reviewed bridge.
- `net_annual_earnings_reference`: `earn_nt_net`, single person without
  children earning 100% of average earnings, EUR/year. This is a
  statistical scenario, NOT a personalized tax calculation or profession wage.

Import only from server cron; each run accepts at most two countries:

```bash
python -m app.eurostat_economy --country PT
python -m app.eurostat_economy --pair DE FR
```

Set `EARNWAGE_INSIGHTS_DB=/home3/policli1/earnwage-private/country_insights.sqlite3`
in the server environment before importing and when running Passenger. The
existing country-insights database gains separate `eurostat_observations`
and `eurostat_refresh` tables; no migration or downloaded SQLite file
is committed. Restart Passenger after deploying the code. An API code
update alone does NOT import Eurostat observations or restart the host.

```text
GET /v1/eurostat/coverage
GET /v1/eurostat/PT/hicp_annual_change_monthly
GET /v1/eurostat/PT/household_price_level_eu27
GET /v1/eurostat/PT/net_annual_earnings_reference
GET /v1/eurostat/compare?country_a=PT&country_b=DE
```

Every response includes actual period, unit, dataset, source URL and refresh
status. The Eurostat importer does not overwrite World Bank CPI/PPP series,
and the app should not mix them as equivalent measures. No live Eurostat
requests occur on these HTTP routes.

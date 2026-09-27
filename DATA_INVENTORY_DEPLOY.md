# EarnWage — complete source-backed data inventory

The repository now provides a **read-only unified catalogue** of the records
actually visible to the current EarnWage API process. It does **not** migrate
the economic and wage databases into one physical SQLite file, and it does not
pretend that a committed file or importer is a successful production refresh.

- Browser: https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-inventory.html
- API JSON: https://earnwage-api.policlinicosdesantoandre.com/v1/data-inventory
- API Lab: https://gilpereirapt.github.io/Global-Purchasing-Power-API/

The inventory audits 14 countries, 13 WDI indicators per country, three
Eurostat/ONS/OECD economic series for nine eligible countries, the complete
14 × 40 exact-occupation wage availability matrix, nine ILOSTAT major groups
per country and the ECB currency cache. Each official indicator includes the
stored value, source, observation period, observation count, last successful
refresh, latest attempted refresh and source URL. Country and source totals
are counts of real observations only.

Exact occupation wages and ISCO-08 major-group wage **contexts** are separate.
The presence of a large-group value does not turn it into the specific
occupation's salary. Historical observation years are distinct from the date
when the database was last refreshed. The ECB cache may be empty or expired
without proving that the ECB does not publish an exchange rate.

## Deploy the API on cPanel/Passenger

GitHub Pages only publishes the browser UI. **A GitHub commit does not itself
update the Python backend running on cPanel.**

Update the deployed code to include at least:

- app/data_inventory.py (new)
- app/native_wsgi.py (new /v1/data-inventory read-only route)
- app/main.py (same contract for ASGI installations)
- Any earlier project updates not yet deployed.

Restart Passenger using the usual application restart procedure. Confirm:

1. GET /v1/health succeeds.
2. GET /v1/data-inventory responds with JSON containing summary and countries.
3. Open the browser UI and verify the same counts.
4. Confirm that EARNWAGE_INSIGHTS_DB and GPP_CACHE_DB are configured as persistent,
   writable absolute SQLite paths in the **server environment**. Do not expose
   these paths publicly or rely on /tmp in production.
5. Verify the actual cPanel cron jobs and their logs, separately. The public
   inventory cannot authenticate that any importer was scheduled or ran
   successfully.

When one of the source imports has not yet been executed, the inventory will
show not_imported or zero observations. Run the relevant validated importer
on the server; opening the inventory **never** triggers an upstream import.

## Refresh mechanisms

- World Bank: python -m scripts.update_country_insights — designed for two
  countries per day, with all 13 indicator series per country. Activate cron
  manually using COUNTRY_INSIGHTS_DEPLOY.md.
- Eurostat, ONS and OECD: python -m app.eurostat_economy --country PT
  (or the explicit pair mode), or the separately secured Eurostat admin route.
- Exact occupation wages: validated ILOSTAT and North American imports and
  snapshots; distinguish national occupation records from major groups.
- Exchange rates: cached ECB response on demand, normally 24-hour TTL.
- Jobs: searches over external feeds, not long-term economic-series inventory.

Use the UI's country, source and status filters to find missing records. Export
CSV or JSON to preserve a dated coverage audit without revealing user accounts
or server secrets. The production API must be deployed before the browser
dashboard can successfully load live data.

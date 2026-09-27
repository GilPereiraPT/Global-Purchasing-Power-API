# EarnWage Country Insights — weekly offline import

# Safe first-time consolidation

For a server with existing data, follow [DATA_CONSOLIDATION.md](DATA_CONSOLIDATION.md) FIRST: verify the exact active database paths, take a verified private SQLite backup, dry-run the missing-only plan, and backfill at most two countries per invocation. Never repoint an existing application to a new empty SQLite database. The production inventory exported on 2026-09-27 had a 12-indicator catalogue; this repository has 13 including GDP per capita, so the coverage denominator changes from 168 to 182 on deployment.

The public endpoints now read **only SQLite**. They do not contact the World
Bank on a user request. Import observations first, or they will correctly show
`not_imported`. The Gallup safety index remains unconnected until reuse rights
and a country-level dataset are confirmed. Do not substitute homicide rates.

## cPanel setup

1. Deploy `app/country_insights.py`, `app/country_insights_store.py`,
   `app/native_wsgi.py`, and `scripts/update_country_insights.py`.
   Keep `app/country_insights_store.py` outside the public static document root
   if your hosting layout permits.
2. Choose an absolute persistent SQLite path **outside public_html**, writable
   by both the cron Python user and the Passenger Python user. Example:
   `/home/CPANEL_USER/earnwage-private/country_insights.sqlite3`.
   Replace `CPANEL_USER` with the real account; the example is not a real path.
3. Set `EARNWAGE_INSIGHTS_DB` to **the same exact path** for both cron and
   Passenger. Set it in the Passenger application environment, not just in cron.
   The development-only fallback `/tmp/earnwage_country_insights.sqlite3`
   must not be relied on for production.
4. From the repository root, using the same Python virtual environment as the
   Passenger application, run once to create the database and import Portugal:

   ```bash
   EARNWAGE_INSIGHTS_DB=/home/CPANEL_USER/earnwage-private/country_insights.sqlite3 /home/CPANEL_USER/virtualenv/APP/3.11/bin/python -m scripts.update_country_insights --country PT
   ```

   Adjust Python and app paths to the real cPanel configuration. Never put
   the database under a web-accessible directory. If the cPanel cron environment
   does not propagate application environment variables, set them in its command.
5. Restart Passenger and check:
   `/v1/countries/PT/indicators` and
   `/v1/countries/PT/indicators/life_expectancy?history=true`.

## Daily cron (two countries, one refresh per country per week)

Run once daily, e.g. at 03:15 **Europe/Lisbon** local time. The script uses
Europe/Lisbon to select the weekday regardless of the host's timezone.
The cron scheduler itself may be in another timezone; adjust the execution
hour if necessary.

```bash
15 3 * * * cd /home/CPANEL_USER/EARNWAGE_APP && EARNWAGE_INSIGHTS_DB=/home/CPANEL_USER/earnwage-private/country_insights.sqlite3 /home/CPANEL_USER/virtualenv/APP/3.11/bin/python -m scripts.update_country_insights >> /home/CPANEL_USER/earnwage-private/insights-cron.log 2>&1
```

Monday PT ES; Tuesday DE FR; Wednesday GB IE; Thursday NL CH;
Friday IT US; Saturday CA BR; Sunday IN PK.

Each of the 13 World Bank indicators is requested **sequentially** with a one-second
pause, for at most 26 requests per day (two countries). A timeout or an empty series never
deletes an older valid observation. The log records each indicator outcome.
A failed run exits with code 1 for monitoring; it does not retry immediately
and will be retried on the next scheduled cycle.

For initial backfill, run `--day 0` through `--day 6` **on separate
occasions**, not all in a single cron invocation. `--country PT` imports
only Portugal. Do not invoke importer via a public endpoint.

## Data semantics

- Each observation retains its original year, unit, source URL, and refresh
  metadata; no interpolation, national ranking or invented composite score.
- `status: available` can coexist with
  `refresh_status: upstream_unavailable`: the last valid value is retained.
- A series with no source observations is not the same as a network error.
- Literacy for Portugal may remain at 2011 until the source publishes a newer
  value. Primary completion may exceed 100% by source methodology.
- `health_coverage` is still mapped to `SH.UHC.SRVS.CV.XD` pending a
  verified replacement. Do not silently switch to a non-equivalent series.
- The SQLite file is operational data; back it up separately from GitHub.

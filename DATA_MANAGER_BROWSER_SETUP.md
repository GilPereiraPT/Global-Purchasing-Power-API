# EarnWage Data Manager — no Terminal required

## What is already prepared in GitHub

- Browser: https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-manager.html
- API endpoints (protected POST, not public GET):
  - /v1/admin/data-manager/status
  - /v1/admin/data-manager/backup
  - /v1/admin/data-manager/import
- Source-backed data inventory:
  https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-inventory.html
- Automatic refresh workflow:
  .github/workflows/earnwage-production-data.yml (initially OPT-IN, not
  considered active until installed, configured and tested).

All writes require the existing private server-side EARNWAGE_ADMIN_TOKEN,
at least 32 characters. The same value is entered directly in the browser
session for manual use, and, separately, into a GitHub Actions secret
named EARNWAGE_ADMIN_TOKEN for scheduled use. Never share the token in chat,
issues, source code, GitHub variables, query strings or screenshots.
The browser uses a fixed HTTPS production host (not a user-entered URL).

## One-time install in cPanel File Manager

Never replace the complete application directory or overwrite SQLite files.
Following the earlier HTTP 500 caused by a broken source encoding, download
the exact GitHub files through the GitHub Raw button and upload them intact,
without cPanel editor paste. Back up existing source files before replacing.

The application root observed in Passenger logs:
  /home3/policli1/api-earnwage/

At minimum sync these files from the current repository:
  app/native_wsgi.py       (updated POST route, GET/health remains unchanged)
  app/data_manager.py      (NEW)
  scripts/backup_earnwage_data.py (NEW)
  app/country_insights.py  (13-series WDI catalogue; 15s import timeout)
  app/eurostat_economy.py  (existing, verify deployed version)
  app/country_insights_store.py (existing, verify deployed version)

No other application file or Android APK is required for the manager.
The GitHub Pages dashboard is deployed automatically by its own workflow.
In cPanel Setup Python App check the EXISTING values, without creating a
new empty database:
  EARNWAGE_INSIGHTS_DB — existing economic SQLite path
  GPP_CACHE_DB — existing wages/cache SQLite path
  EARNWAGE_ADMIN_TOKEN — private 32+ character administrator token

If absent, use the cPanel Setup Python App environment-variable controls.
Do not repoint either of the first two variables to a new file.
The manager refuses a backup if those database paths are not explicitly
configured, missing, or point to unsafe destinations. It creates private
backup files below the application root at _earnwage_backups/, NOT public_html.
Do not publish that directory and check hosting disk quota regularly.

Restart Python App through the cPanel interface.

First verify:
  https://earnwage-api.policlinicosdesantoandre.com/v1/health
  https://earnwage-api.policlinicosdesantoandre.com/v1/data-inventory
Then open:
  https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-manager.html

Press "Verificar acesso e estado". If the admin route is not deployed,
the browser will report HTTP 404. If token is absent/mismatched it will
report 503/401 respectively. Resolve via the cPanel GUI; do not
put secret values into troubleshooting screenshots.

Press "Criar e verificar cópia de segurança" ONCE before any imports.
The server uses SQLite's online-backup API and integrity_check for both
existing stores and saves any present source snapshots. Only the backup
identifier and successful integrity result are exposed via admin HTTP.

Use the browser to preview PT annual inflation, then import PT annual
inflation and household-consumption PPP. Check values/year/source and
the inventory before using "all countries" with missing-only. Keep
health_coverage/UHC separate until the official series is re-validated.
Never substitute a major ILOSTAT group wage for a precise occupation wage.

## One-time scheduled automation through GitHub Settings (no Terminal)

Only AFTER the production Data Manager has been deployed and the manual
backup/import has succeeded:

1. In GitHub repository Settings -> Secrets and variables -> Actions ->
   Secrets, add repository SECRET EARNWAGE_ADMIN_TOKEN, matching the private
   value already used in cPanel. Do not put the token in Variables.
2. In Actions -> Variables, add repository VARIABLE
   EARNWAGE_SCHEDULE_ENABLED = true.
3. In Actions tab, select "EarnWage production data refresh". First use
   Run workflow with source world_bank, country PT, mode missing, and
   essentials checked. Verify the workflow run and the inventory.
4. Confirm scheduled runs appear after the next UTC cron triggers.

The workflow starts at 04:21 UTC (WDI: two countries by Lisbon weekday,
13 configured series each) and 05:21 UTC (Eurostat/ONS/OECD: up to two
European countries by weekday; three series each). GitHub Actions cron
may be delayed. Both schedules share a concurrency group; imports are
serialized by the API's cross-worker lock. Once per Monday scheduled WDI
run an additional private backup is created; the script also creates
one if none exists yet. Check disk space and prune backups MANUALLY only
after verifying retained copies. Do not delete all recovery copies.

For scheduled runs, mode REFRESH always re-queries observations even when
a previous value exists. Browser mode MISSING skips existing values and is
intended only for initial backfill. Requests preserve prior values if a
source is unavailable and write a result to the audit table.

The ECB exchange-rate cache retains the prior on-demand 24-hour policy.
Exact ILOSTAT, BLS and Canada Job Bank salary snapshot workflows have
their own source-schema review process and are NOT automatically enabled
by this Data Manager: scheduled World Bank/Eurostat jobs must not be
mistaken for complete automated updates of every official data source.

## Security / operations

- The new HTTP imports require POST plus an admin token in an HTTP HEADER.
  No secrets are accepted in URLs. CORS is limited to EarnWage GitHub Pages.
- A preview makes no network request and writes no source observations.
- One import = one country/indicator, bounded by the source's timeout;
  no arbitrary Python shell commands or remote URLs are accepted.
- A storage/backup failure does not deliberately erase existing values.
- Data Manager activity is separate from the existing source refresh logs.
- Use the Inventory for real, dated coverage. A successful scheduled run
  does not mean the upstream publisher released new data on that date.

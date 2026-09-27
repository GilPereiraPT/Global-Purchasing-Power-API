# EarnWage — safe consolidation of production data

## Baseline (exported 2026-09-27 18:22 UTC)
14 countries; 104/168 WDI country-indicator cells; 3,462 WDI history observations;
27/27 Eurostat/ONS/OECD cells; 3,671 economic history observations;
38/560 exact country-occupation pairs (66 observations, none from exact ILOSTAT);
117/126 ILOSTAT major-group pairs (630 local-currency observations).
Annual CPI inflation and household-consumption PPP were absent in all 14 countries:
28 cells. UHC health_coverage had upstream failures for all 14 countries.
The deployed inventory had 12 WDI series; the latest repository has 13,
including gdp_per_capita. After deploying that catalogue, coverage has
182 possible cells instead of 168; distinguish catalogue changes from new data.

## Safety: after previous UTF-8 / Passenger 500
Check /v1/health and /v1/data-inventory before doing anything.
Do NOT replace app/native_wsgi.py or touch the Android APK in this phase.
Download source files via GitHub Raw as intact UTF-8, not cPanel editor paste.
Back up actual, existing SQLite files and snapshots first. No migrations needed.

Update initially only:
- app/country_insights.py (15 s source timeout; latest 13-series catalogue)
- scripts/update_country_insights.py (targeted, missing-only, no-network dry-run)
- scripts/backup_earnwage_data.py (new safe online backup command).

## 1. Back up EXACT in-use databases and snapshots
In cPanel Setup Python App, obtain the existing persistent paths for
EARNWAGE_INSIGHTS_DB (WDI, Eurostat) and GPP_CACHE_DB (wages, ECB cache).
Provide the same existing values in the activated terminal Python environment.
Do NOT point them to newly created files during this operation. If GPP_CACHE_DB
was absent and /tmp is used, back up the actual file before reconfiguring.
Run from the project root on the same activated Python environment:

    cd /home3/policli1/api-earnwage
    python -m scripts.backup_earnwage_data --output /home3/policli1/earnwage-backups/initial-consolidation-01

The script refuses missing source DBs or an existing output dir, refuses
public_html, uses SQLite online backup, verifies SQLite integrity and
copies any committed local snapshot files. Keep the private backup directory.

## 2. Preview without any network or database writes

    python -m scripts.update_country_insights --country PT --missing-only --dry-run

Inspect would_import and skipped_existing. If already-available PT data
looks missing, STOP: the terminal is pointed at a different database.

## 3. Fill essential annual inflation and household consumption PPP
Pilot Portugal, then query the two returned API indicators:

    python -m scripts.update_country_insights --country PT --indicator inflation_annual --indicator ppp_private_consumption --missing-only

    /v1/countries/PT/indicators/inflation_annual
    /v1/countries/PT/indicators/ppp_private_consumption

Only after seeing numeric values, source and year, complete the other countries
in separately scheduled invocations of the existing two-country weekday pairs:

    python -m scripts.update_country_insights --day 0 --indicator inflation_annual --indicator ppp_private_consumption --missing-only

Repeat with --day 1 through --day 6. (0 PT/ES; 1 DE/FR; 2 GB/IE;
3 NL/CH; 4 IT/US; 5 CA/BR; 6 IN/PK). Exit status 1 flags upstream failures;
it does not erase valid older observations. Check logs before another batch.

## 4. Verify catalogue drift and fill GDP separately
Check the production /v1/indicators catalogue after deploying the new source
module; make sure it includes gdp_per_capita. Then run:

    python -m scripts.update_country_insights --country PT --indicator gdp_per_capita --missing-only

When successful, repeat --day 0 through 6 on separate occasions, with
--indicator gdp_per_capita --missing-only. After that, rerun remaining missing
WDI cells selectively by weekday pair with --missing-only.

Do NOT add --missing-only to the normal weekly refresh cron: it is intended
for one-off backfilling and deliberately skips already-available series.

## 5. UHC series requires source review
The existing health_coverage key maps to SH.UHC.SRVS.CV.XD
(original published World Bank metadata reports observations through 2021).
A different published WHO/World Bank identifier, SH_UHC_SCI, shows years
through 2023. A similar label is insufficient evidence to overwrite the
historical records with a different series: confirm lineage and methodology
before a separately versioned mapping. Diagnose one country first.

## 6. Exact occupation wages
The export shows no exact ILOSTAT salary snapshot and no observed exact
ILOSTAT jobs. We do have distinct major-group wage contexts, which are
NOT exact-occupation wages. Use the existing read-only ILOSTAT workflow
diagnostic before trying the committing official snapshot import.
Only a validated, non-empty data/salaries_snapshot.json deployed to the
server can increase exact ILOSTAT coverage.

## 7. Operations
Inspect actual cPanel cron settings and logs; a script in GitHub does not
prove that cron is running. Keep the two-country weekly refresh for every
indicator without missing-only. Re-export the same /v1/data-inventory JSON
after each stage and compare values, source years, last refresh, and
available cells, allowing for the 168 -> 182 catalogue denominator change.

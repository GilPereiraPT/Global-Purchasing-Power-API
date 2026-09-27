# EarnWage — official open-data wave: safety, corruption, work and well-being

Status: **code catalogue and tests**, not a claim of imported production observations.

## Catalogue: 13 to 29 WDI/WHO series
14 supported countries × 29 series = **406 possible country-series cells**.
Availability is calculated only from rows stored in the deployed SQLite database.
The existing 13 series, server paths, snapshots and hourly/daily imports are not
replaced. The inventory denominator changes from 182 to 406 **when this code is deployed**.

### New WDI series (all source pages display CC BY 4.0)
| Family | API name | WDI code | Unit |
|---|---|---|---|
| Safety | intentional_homicides | VC.IHR.PSRC.P5 | per 100,000 people |
| Safety | intentional_homicides_female | VC.IHR.PSRC.FE.P5 | per 100,000 females |
| Safety | intentional_homicides_male | VC.IHR.PSRC.MA.P5 | per 100,000 males |
| Safety | political_stability | GOV_WGI_PV_SC | governance score 0–100 |
| Safety | rule_of_law | GOV_WGI_RL_SC | governance score 0–100 |
| Safety | battle_related_deaths | VC.BTL.DETH | number of people |
| Corruption | control_of_corruption | GOV_WGI_CC_SC | governance score 0–100 |
| Corruption | bribery_incidence_firms | IC.FRM.BRIB.ZS | % of firms surveyed |
| Corruption | tax_official_gifts_firms | IC.TAX.GIFT.ZS | % of firms surveyed |
| Employment | youth_unemployment | SL.UEM.1524.ZS | % labour force ages 15–24 |
| Employment | employment_population_ratio | SL.EMP.TOTL.SP.ZS | % population ages 15+ |
| Employment | advanced_education_unemployment | SL.UEM.ADVN.ZS | % advanced-education labour force |
| Health | physicians | SH.MED.PHYS.ZS | per 1,000 people |
| Health | hospital_beds | SH.MED.BEDS.ZS | per 1,000 people |
| Health | out_of_pocket_health_expenditure | SH.XPD.OOPC.CH.ZS | % current health expenditure |
| Environment | pm25_air_pollution | EN.ATM.PM25.MC.M3 | µg/m³ |

The source page is `https://data.worldbank.org/indicator/{CODE}`.
The actual import endpoint is
`https://api.worldbank.org/v2/country/{ISO3}/indicator/{CODE}?format=json&per_page=1000`.

**Interpretation:**
- The three homicide indicators are rates with different denominators; they are
  not raw homicide totals and should not be added.
- WGI governance scores are perception-based 0–100 indices; they are not
  corruption/crime incident percentages. Do not mix revised and old WGI methods.
- Enterprise Surveys concern sampled private firms, not every resident or firm,
  and may have few or no observations for a particular country/year.
- Battle-related deaths are absolute counts from UCDP. Missing means missing,
  not zero; do not substitute this measure for all conflict-related deaths.
- Out-of-pocket expenditure is a share of total **national health expenditure**,
  not the percentage of a particular person's salary spent on health.
- PM2.5 is national annual exposure, not city or street pollution.
- No data point is labelled as a capital/city result. The recorded statistical
  year is distinct from last successful import time.

## Deploy / import safely (server administrator)

1. Confirm `GET /v1/health` and export existing `GET /v1/data-inventory`.
2. Back up the **existing** databases and snapshots using
   `python -m scripts.backup_earnwage_data --output PRIVATE_NEW_DIRECTORY`;
   keep the configured `EARNWAGE_INSIGHTS_DB` and `GPP_CACHE_DB` values.
3. Deploy only the reviewed API changes including
   `app/country_insights.py` and `app/country_insights_store.py`.
   Restart Passenger. Do not replace `app/native_wsgi.py` or the Android APK.
4. Confirm `/v1/health` still succeeds and `/v1/indicators` includes the new
   names. Existing 13-series observations must still be present. Check the new
   406-cell inventory denominator and existing observed count (do not expect
   406 observed).
5. Dry run one country and only the new series, e.g.:

   `python -m scripts.update_country_insights --country PT --indicator intentional_homicides --indicator control_of_corruption --indicator physicians --missing-only --dry-run`

6. Import the same pilot **without** `--dry-run` after validating the plan.
   Inspect `/v1/countries/PT/indicators/intentional_homicides?history=true`,
   `/v1/countries/PT/indicators/control_of_corruption?history=true` and
   `/v1/countries/PT/indicators/physicians?history=true`.
7. Finish the other series and countries as at most two countries per run,
   reusing `--day 0` through `--day 6` with `--missing-only` for the
   *one-off backfill*. **Do not add `--missing-only` to normal weekly refresh.**
8. Export a second inventory and compare sources, years, stored observations,
   failed imports, and not-imported/empty statuses. Inspect actual cPanel cron
   configuration and logs; GitHub workflows do not prove cron ran on cPanel.

## Deliberately NOT included

- Numbeo and GPI licensed/commercial redistribution.
- City crime rates inferred from national figures.
- Homicide/missing conflict data imputed as zero.
- A fabricated combined safety/corruption/quality-of-life ranking.
- Eurostat housing-cost-overburden `ilc_lvho07a` is a separate European
  family, not a WDI series and not a 14-country dataset; it needs its own importer.

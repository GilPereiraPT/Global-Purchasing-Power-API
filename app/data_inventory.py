"""Read-only, source-specific inventory of the REAL EarnWage server data.

An inventory is not an importer and does not assume that a committed snapshot
is already deployed/imported. Inspect observations in each server database.
Keep public output free of filesystem paths, personal data and secret settings.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app.country_insights import INDICATORS, SOURCE as WB_SOURCE
from app.country_insights_store import connect as insights_connect, read_indicator
from app.eurostat_economy import EUROSTAT_COUNTRIES, SERIES, ensure_tables, read as euro_read
from app.ilostat_groups import load_snapshot as load_groups, SOURCE_URL as GROUP_SOURCE
from app.ilostat_import import init_salary_db
from app.north_america import init as init_north_america
from app.pt_occupation_wages import init as init_pt_wages
from app.es_eaes_groups import catalogue as es_eaes_catalogue, SOURCE_URL as ES_GROUP_SOURCE
from app.store import connect as cache_connect

ROOT = Path(__file__).resolve().parent.parent
CURRENCIES = ("EUR", "USD", "GBP", "CAD", "CHF", "BRL", "INR", "PKR")
FX_TTL_SECONDS = 86400


def _history(db, table, column, country, indicator):
    # Table/column are *only* internal constants, never request parameters.
    row = db.execute(
        "SELECT COUNT(*), MIN(" + column + "), MAX(" + column + ") FROM " +
        table + " WHERE country=? AND indicator=?",
        (country, indicator),
    ).fetchone()
    return {"observations": int(row[0]), "first_period": row[1],
            "last_period": row[2]}


def _observation(item, history):
    return {
        "status": item["status"], "value": item["value"],
        "period": item.get("year", item.get("period")),
        "unit": item["unit"], "source": item["source"],
        "source_url": item["source_url"],
        "last_successful_refresh": item.get("last_successful_refresh"),
        "last_attempt": item.get("last_attempt"),
        "refresh_status": item.get("refresh_status"),
        **({"family": item["family"]} if "family" in item else {}),
        **({"underlying_source": item["underlying_source"]} if "underlying_source" in item else {}),
        **history,
    }


def _wages(db):
    init_salary_db(db)
    init_north_america(db)
    init_pt_wages(db)
    ilo = db.execute(
        """SELECT country,occupation,COUNT(*),MAX(period)
           FROM salary_observations GROUP BY country,occupation"""
    ).fetchall()
    na = db.execute(
        """SELECT country,occupation,COUNT(*),MAX(reference_period)
           FROM north_america_wages GROUP BY country,occupation"""
    ).fetchall()
    pt = db.execute("""SELECT country,occupation,COUNT(*),MAX(period)
         FROM pt_occupation_wages GROUP BY country,occupation""").fetchall()
    return {
        "INE_GEP": {(country, occupation): (count, str(period))
                    for country, occupation, count, period in pt},
        "ILOSTAT": {(country, occupation): (count, str(period))
                    for country, occupation, count, period in ilo},
        "BLS_Canada_Job_Bank": {
            (country, occupation): (count, str(period))
            for country, occupation, count, period in na},
    }


def _rates(db):
    now = int(time.time())
    data = {"EUR": {"status": "identity", "period": None, "source": "identity",
                    "fetched_at": None, "age_seconds": None}}
    for code in CURRENCIES:
        if code == "EUR":
            continue
        record = db.execute(
            "SELECT response,fetched_at FROM cache WHERE cache_key=?",
            ("ecb:exchange:" + code,),
        ).fetchone()
        if not record:
            data[code] = {"status": "not_cached", "period": None,
                          "source": "ECB", "fetched_at": None, "age_seconds": None}
            continue
        try:
            content = json.loads(record[0])
        except (ValueError, TypeError):
            content = {}
        age = max(0, now - int(record[1]))
        data[code] = {
            "status": "cached" if age <= FX_TTL_SECONDS else "expired",
            "period": content.get("period"), "source": content.get("source", "ECB"),
            "fetched_at": datetime.fromtimestamp(int(record[1]), timezone.utc).isoformat(),
            "age_seconds": age,
        }
    return data


def build_inventory():
    """One snapshot of all configured countries and indicator families.

    Numbers are computed from stored rows; zero does not mean a source does
    not publish the statistic, and an importer script is not an active cron.
    """
    with insights_connect() as economic_db, cache_connect() as wage_db:
        ensure_tables(economic_db)
        salaries = _wages(wage_db)
        rates = _rates(wage_db)
        es_groups = es_eaes_catalogue()
        raw_groups = load_groups()
        groups = {}
        for row in raw_groups:
            if row.get("unit_type") != "local_currency":
                continue
            country = row.get("country")
            group = str(row.get("isco08_major_group", ""))
            if country not in COUNTRY_MAP or group not in map(str, range(1, 10)):
                continue
            groups.setdefault((country, group), []).append(row)

        result = []
        summary = {
            "world_bank": {"available": 0, "possible": len(COUNTRY_MAP) * len(INDICATORS),
                           "historical_observations": 0},
            "eurostat_ons_oecd": {
                "available": 0,
                "possible": len(EUROSTAT_COUNTRIES) * len(SERIES),
                "historical_observations": 0},
            "exact_occupational_wages": {
                "observed_pairs": 0,
                "possible_pairs": len(COUNTRY_MAP) * len(OCCUPATIONS),
                "stored_observations": 0,
                "by_source_observations": {"ILOSTAT": 0, "BLS_Canada_Job_Bank": 0, "INE_GEP": 0}},
            "ilostat_major_groups": {
                "observed_pairs": 0, "possible_pairs": len(COUNTRY_MAP) * 9,
                "stored_observations": 0},
            "es_ine_eaes_groups": {
                "country": "ES", "status": es_groups["status"],
                "published_observations": es_groups.get("published_observations", 0),
                "high_variability_observations": es_groups.get("high_variability_observations", 0),
                "suppressed_or_missing": es_groups.get("suppressed_or_missing", 0),
                "group_count": es_groups.get("group_count", 0),
                "precision": "cno11_major_group_not_exact_occupation"},
        }
        for country, details in COUNTRY_MAP.items():
            wb = {}
            for name in INDICATORS:
                item = read_indicator(economic_db, country, name)
                history = _history(economic_db, "observations", "year", country, name)
                wb[name] = _observation(item, history)
                summary["world_bank"]["historical_observations"] += history["observations"]
                if item["status"] == "available":
                    summary["world_bank"]["available"] += 1

            euro = {}
            if country in EUROSTAT_COUNTRIES:
                for name in SERIES:
                    item = euro_read(economic_db, country, name)
                    history = _history(economic_db, "eurostat_observations",
                                       "period", country, name)
                    euro[name] = _observation(item, history)
                    summary["eurostat_ons_oecd"]["historical_observations"] += (
                        history["observations"])
                    if item["status"] == "available":
                        summary["eurostat_ons_oecd"]["available"] += 1

            occupations = {}
            exact_available = 0
            for job in OCCUPATIONS:
                key = (country, job["id"])
                sources = []
                for provider, records in salaries.items():
                    if key in records:
                        count, period = records[key]
                        sources.append({"source": provider, "observations": count,
                                        "latest_period": period})
                        summary["exact_occupational_wages"]["stored_observations"] += count
                        summary["exact_occupational_wages"]["by_source_observations"][
                            provider] += count
                if sources:
                    exact_available += 1
                    summary["exact_occupational_wages"]["observed_pairs"] += 1
                occupations[job["id"]] = {
                    "status": "available" if sources else "not_imported",
                    "sources": sources,
                }

            major_groups = {}
            for major in range(1, 10):
                group = str(major)
                rows = groups.get((country, group), [])
                if rows:
                    summary["ilostat_major_groups"]["observed_pairs"] += 1
                    summary["ilostat_major_groups"]["stored_observations"] += len(rows)
                major_groups[group] = {
                    "status": "available" if rows else "not_imported",
                    "observations": len(rows),
                    "latest_period": max((r.get("period", "") for r in rows),
                                         default=None),
                }
            result.append({
                "code": country, "name": details["name"],
                "currency": details["currency"],
                "world_bank": wb,
                "eurostat_ons_oecd": euro,
                "exact_occupational_wages": {
                    "available_occupations": exact_available,
                    "total_catalogue_occupations": len(OCCUPATIONS),
                    "occupations": occupations},
                "ilostat_major_groups": major_groups,
                "es_ine_eaes_groups": es_groups if country == "ES" else {"status": "not_applicable"},
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "country_count": len(COUNTRY_MAP),
        "summary": summary,
        "countries": result,
        "exchange_rates": rates,
        "source_registry": {
            "world_bank": {
                "source": "World Bank WDI",
                "indicator_count": len(INDICATORS),
                "importer": "scripts/update_country_insights.py",
                "update_mechanism": "scheduled_import_if_cron_configured",
                "example_source_url": WB_SOURCE.format(
                    country="PRT", indicator="SP.DYN.LE00.IN")},
            "eurostat_ons_oecd": {
                "source": "Eurostat, ONS, OECD (depending on country and indicator)",
                "indicator_count": len(SERIES),
                "importer": "app/eurostat_economy.py",
                "update_mechanism": "explicit_import_not_http_request"},
            "exact_occupational_wages": {
                "source": "ILOSTAT, BLS, Canada Job Bank, INE/GEP Quadros de Pessoal",
                "importers": ["app/ilostat_import.py", "app/north_america.py",
                              "app/pt_occupation_wages.py"],
                "update_mechanism": "validated_import_and_startup_snapshot"},
            "ilostat_major_groups": {
                "source": "ILOSTAT",
                "source_url": GROUP_SOURCE,
                "update_mechanism": "validated_local_snapshot",
                "precision": "ISCO-08 major group, not exact occupation salary"},
            "es_ine_eaes_groups": {
                "source": "INE Spain, Encuesta Anual de Estructura Salarial",
                "source_url": ES_GROUP_SOURCE,
                "precision": "CNO-11 broad group, never individual profession",
                "update_mechanism": "committed_official_publication_snapshot"},
            "exchange_rates": {
                "source": "ECB",
                "update_mechanism": "24_hour_on_demand_cache",
                "note": "A missing or expired cache does not mean ECB data is unavailable."},
            "job_ads": {
                "source": "External jobs feeds",
                "update_mechanism": "live_search_and_cache",
                "note": "Not part of the long-term statistical observations inventory."},
        },
        "deployment": {
            "source_snapshots_on_server": {
                "ilostat_exact": (ROOT / "data" / "salaries_snapshot.json").is_file(),
                "north_america": (ROOT / "data" / "north_america_wages.json").is_file(),
                "portugal_ine_gep": (ROOT / "data" / "pt_occupation_wages.json").is_file(),
                "spain_ine_eaes_groups": (ROOT / "data" / "es_ine_eaes_28186.json").is_file(),
                "ilostat_major_groups":
                    (ROOT / "data" / "ilostat_group_salaries.json").is_file(),
            },
            "cron_running": "not_verifiable_from_http",
            "note": ("Source snapshot files and importer code do not prove that the "
                     "latest upstream observations were imported or that cron runs."),
        },
        "notes": [
            "This endpoint inventories the actual rows readable by the current API worker.",
            "Latest source observation year differs from the database refresh date.",
            "Eurostat/ONS/OECD and World Bank inflation are distinct series.",
            "Exact occupation wages are separate from ISCO-08 major-group wages.",
            "Missing means no row found here; it is not a claim the official source has no data.",
            "Public inventory contains no personal accounts, credentials or server paths.",
        ],
    }

"""Persistent, read-only-on-HTTP country indicator store.

Set EARNWAGE_INSIGHTS_DB to an absolute, writable SQLite file outside public_html.
The importer is the only component that makes external World Bank requests.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.country_insights import ISO3, INDICATORS, INDICATOR_METADATA, SOURCE, UHC_SERIES


def db_path():
    configured = os.environ.get("EARNWAGE_INSIGHTS_DB")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise ValueError("EARNWAGE_INSIGHTS_DB must be an absolute path")
        return path
    # Development fallback only; configure an explicit persistent path on cPanel.
    return Path("/tmp/earnwage_country_insights.sqlite3")


def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=15)
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS observations (
        country TEXT NOT NULL,
        indicator TEXT NOT NULL,
        year INTEGER NOT NULL,
        value REAL NOT NULL,
        imported_at TEXT NOT NULL,
        PRIMARY KEY (country, indicator, year)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS refresh_log (
        country TEXT NOT NULL,
        indicator TEXT NOT NULL,
        last_attempt TEXT NOT NULL,
        last_success TEXT,
        status TEXT NOT NULL,
        error_type TEXT,
        PRIMARY KEY (country, indicator)
    )""")
    db.commit()
    return db


def save_result(db, country, name, observations, status, error_type=None):
    """Never delete existing observations on empty results or failed refresh."""
    now = datetime.now(timezone.utc).isoformat()
    if status == "available" and observations:
        db.executemany(
            """INSERT INTO observations(country,indicator,year,value,imported_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(country,indicator,year)
               DO UPDATE SET value=excluded.value, imported_at=excluded.imported_at""",
            [(country, name, int(row["year"]), float(row["value"]), now)
             for row in observations])
    success = now if status == "available" else None
    db.execute(
        """INSERT INTO refresh_log(country,indicator,last_attempt,last_success,status,error_type)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(country,indicator) DO UPDATE SET
             last_attempt=excluded.last_attempt,
             last_success=COALESCE(excluded.last_success,refresh_log.last_success),
             status=excluded.status,error_type=excluded.error_type""",
        (country, name, now, success, status, error_type))
    db.commit()


def read_indicator(db, country, name, year=None, history=False):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    if name not in INDICATORS:
        raise ValueError("Unknown indicator")
    if year is not None and (not isinstance(year, int) or not 1960 <= year <= 2100):
        raise ValueError("Invalid year")
    code, unit = INDICATORS[name]
    records = db.execute(
        """SELECT year,value FROM observations
           WHERE country=? AND indicator=? ORDER BY year DESC""",
        (country, name)).fetchall()
    matching = [{"year": y, "value": v} for y, v in records
                if year is None or y == year]
    row = matching[0] if matching else None
    log = db.execute(
        """SELECT last_attempt,last_success,status,error_type FROM refresh_log
           WHERE country=? AND indicator=?""", (country, name)).fetchone()
    status = ("available" if row else "unavailable" if log and log[2] == "available"
              else "not_imported" if not log else log[2])
    result = {
        "country": country, "iso3": ISO3[country], "name": name,
        "indicator_code": code, "unit": unit,
        "status": status, "value": row["value"] if row else None,
        "year": row["year"] if row else None, "requested_year": year,
        "source": "World Bank World Development Indicators",
        "source_url": SOURCE.format(country=ISO3[country], indicator=code),
        "note": "Latest locally stored non-null observation; years may differ across countries and indicators. No interpolation.",
        "last_attempt": log[0] if log else None,
        "last_successful_refresh": log[1] if log else None,
        "refresh_status": log[2] if log else "not_imported",
    }
    metadata = INDICATOR_METADATA.get(name)
    if metadata:
        result["family"], result["underlying_source"] = metadata
        if name in ("political_stability", "rule_of_law", "control_of_corruption"):
            result["note"] += " Revised WGI perception-based governance score, not a percentage of people or a crime count."
        elif name in ("bribery_incidence_firms", "tax_official_gifts_firms"):
            result["note"] += " Enterprise Survey sample; not an annual census or a measure of all households."
        elif name == "battle_related_deaths":
            result["note"] += " Absolute conflict-related deaths; no record must never be interpreted as zero."
        elif name == "pm25_air_pollution":
            result["note"] += " Estimated national population-weighted PM2.5 exposure; not a city air-quality reading."
    if name == "health_coverage":
        result["source"] = "WHO Global Health Observatory, mirrored by World Bank"
        result["source_url"] = ("https://ghoapi.azureedge.net/api/UHC_INDEX_REPORTED")
        result["world_bank_mirror_url"] = SOURCE.format(
            country=ISO3[country], indicator=code)
        result["who_indicator_code"] = "UHC_INDEX_REPORTED"
        result["sdg_indicator"] = "3.8.1"
        result["methodology"] = UHC_SERIES["methodology"]
        result["methodology_url"] = UHC_SERIES["methodology_url"]
        result["legacy_indicator_code"] = UHC_SERIES["legacy"]
        result["note"] += " " + UHC_SERIES["note"]
    if history:
        result["history"] = matching
    if log and log[3]:
        result["error_type"] = log[3]
    if row and log and log[2] != "available":
        result["note"] += " Last refresh failed; previous verified value retained."
    return result

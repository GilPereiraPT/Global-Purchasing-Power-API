"""Cron-only Eurostat economic indicators, no API keys or HTTP-time fetching.

Keep Eurostat observations separate from World Bank series and retain periods,
exact dimension selections and source links. Run on the server via cron.
"""
import argparse
import re
import json
import math
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.country_insights_store import connect

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
ONS_CPI_URL = ("https://api.beta.ons.gov.uk/v1/data?uri="
               "/economy/inflationandpriceindices/timeseries/d7g7/mm23")
ONS_CPI_SOURCE = "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23"
OECD_UK_NET_SOURCE = "https://www.oecd.org/en/publications/taxing-wages-2026_3a5169ef-en/full-report/evolution-of-effective-tax-rates-on-labour-income-2000-25_5aed550b.html"
# OECD Taxing Wages 2026, table 6.26, GBP, single/no children/100% average wage.
# Publication snapshot: explicit years; do not represent as a live OECD API feed.
OECD_UK_NET_GBP = [("2024", 41074.0), ("2025", 43027.0)]
EUROSTAT_COUNTRIES = ("PT", "ES", "DE", "FR", "IE", "NL", "IT", "GB", "CH")
# Explicit selections avoid mixing index with inflation rate or net with gross.
SERIES = {
    "hicp_annual_change_monthly": {
        "dataset": "prc_hicp_minr",
        "filters": {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL"},
        "unit": "percent_year_on_year", "frequency": "monthly",
        "description": "All-items HICP annual rate of change for the stated month",
    },
    "household_price_level_eu27": {
        "dataset": "prc_ppp_ind",
        "filters": {"freq": "A", "na_item": "PLI_EU27_2020", "ppp_cat": "E011"},
        "unit": "eu27_2020_equals_100", "frequency": "annual",
        "description": "Household final consumption price-level index (COICOP 1999)",
    },
    "net_annual_earnings_reference": {
        "dataset": "earn_nt_net",
        "filters": {"freq": "A", "currency": "EUR", "estruct": "NET",
                    "ecase": "P1_NCH_AW100"},
        "unit": "EUR_per_year", "frequency": "annual",
        "description": "Single person without children at 100% average earnings; statistical reference, not personal tax estimate",
    },
}


def source_url(country, spec):
    if country == "GB" and spec["dataset"] == "prc_hicp_minr":
        return ONS_CPI_SOURCE
    if country == "GB" and spec["dataset"] == "earn_nt_net":
        return OECD_UK_NET_SOURCE
    return BASE + spec["dataset"] + "?" + urlencode(
        {"geo": "UK" if country == "GB" else country, "lang": "EN", **spec["filters"]})


def decode(payload, country, spec):
    """Reject unexpected or ambiguous JSON-stat dimensions rather than guess."""
    dimensions, sizes = payload["id"], payload["size"]
    expected = {"geo", "time", *spec["filters"]}
    if set(dimensions) != expected or len(dimensions) != len(sizes):
        raise ValueError("Unexpected Eurostat dimensions")
    chosen = {"geo": "UK" if country == "GB" else country, **spec["filters"]}
    indexes = {}
    for name in dimensions:
        mapping = payload["dimension"][name]["category"]["index"]
        if name == "time":
            indexes[name] = mapping
        else:
            if chosen[name] not in mapping:
                return []
            indexes[name] = mapping[chosen[name]]
    values = payload.get("value", {})
    results = []
    for period, offset in sorted(indexes["time"].items()):
        linear = 0
        for name, size in zip(dimensions, sizes):
            linear = linear * size + (offset if name == "time" else indexes[name])
        value = values.get(str(linear)) if isinstance(values, dict) else values[linear]
        if value is None:
            continue
        number = float(value)
        if not math.isfinite(number):
            continue
        if spec["frequency"] == "annual":
            if not (len(period) == 4 and period.isdigit()):
                continue
        elif not (len(period) == 7 and period[:4].isdigit()
                  and period[4] == "-" and period[5:].isdigit()
                  and 1 <= int(period[5:]) <= 12):
            continue
        results.append((period, number))
    return results


def ensure_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS eurostat_observations (
        country TEXT NOT NULL, indicator TEXT NOT NULL, period TEXT NOT NULL,
        value REAL NOT NULL, imported_at TEXT NOT NULL,
        PRIMARY KEY(country,indicator,period))""")
    db.execute("""CREATE TABLE IF NOT EXISTS eurostat_refresh (
        country TEXT NOT NULL, indicator TEXT NOT NULL, attempted_at TEXT NOT NULL,
        succeeded_at TEXT, status TEXT NOT NULL, error_type TEXT,
        PRIMARY KEY(country,indicator))""")
    db.commit()


def save(db, country, name, observations, status, error_type=None):
    now = datetime.now(timezone.utc).isoformat()
    if observations and status == "available":
        db.executemany("""INSERT INTO eurostat_observations
            (country,indicator,period,value,imported_at) VALUES (?,?,?,?,?)
            ON CONFLICT(country,indicator,period) DO UPDATE SET
            value=excluded.value, imported_at=excluded.imported_at""",
            [(country, name, period, value, now) for period, value in observations])
    db.execute("""INSERT INTO eurostat_refresh
        (country,indicator,attempted_at,succeeded_at,status,error_type)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(country,indicator) DO UPDATE SET
        attempted_at=excluded.attempted_at,
        succeeded_at=COALESCE(excluded.succeeded_at,eurostat_refresh.succeeded_at),
        status=excluded.status,error_type=excluded.error_type""",
        (country, name, now, now if status == "available" else None,
         status, error_type))
    db.commit()


def read(db, country, name):
    if country not in EUROSTAT_COUNTRIES or name not in SERIES:
        raise ValueError("Unsupported country or Eurostat indicator")
    ensure_tables(db)
    spec = SERIES[name]
    row = db.execute("""SELECT period,value FROM eurostat_observations
        WHERE country=? AND indicator=? ORDER BY period DESC LIMIT 1""",
        (country, name)).fetchone()
    log = db.execute("""SELECT attempted_at,succeeded_at,status,error_type
        FROM eurostat_refresh WHERE country=? AND indicator=?""",
        (country, name)).fetchone()
    ons_cpi = country == "GB" and name == "hicp_annual_change_monthly"
    oecd_net = country == "GB" and name == "net_annual_earnings_reference"
    return {
        "country": country, "name": name, "status": "available" if row else
        (log[2] if log else "not_imported"),
        "value": row[1] if row else None, "period": row[0] if row else None,
        "unit": "GBP_per_year" if oecd_net else spec["unit"], "frequency": spec["frequency"],
        "description": ("UK CPI annual rate, all items; ONS D7G7, not Eurostat HICP"
                        if ons_cpi else
                        "OECD Taxing Wages table 6.26: single, no children, 100% average wage; GBP/year"
                        if oecd_net else spec["description"]),
        "source": "ONS" if ons_cpi else "OECD" if oecd_net else "Eurostat",
        "dataset": "MM23/D7G7" if ons_cpi else "Taxing Wages 2026 Table 6.26" if oecd_net else spec["dataset"], "source_url": source_url(country, spec),
        "last_attempt": log[0] if log else None,
        "last_successful_refresh": log[1] if log else None,
        "refresh_status": log[2] if log else "not_imported",
        "error_type": log[3] if log else None,
        "note": ("UK CPI is not identical to the Eurostat HICP series; do not silently treat them as equivalent. "
                 if ons_cpi else
                 "OECD published annual reference in GBP, not EUR; do not compare nominal values across currencies. "
                 if oecd_net else "National observation; periods can differ. ")
                + "Previous values remain after a failed refresh.",
    }


def decode_ons_cpi(payload):
    """Read ONS D7G7 monthly observations, rejecting non-monthly/invalid values."""
    months = payload.get("months")
    if not isinstance(months, list):
        raise ValueError("ONS D7G7 monthly series missing")
    observations = {}
    month_names = {name: i for i, name in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG",
         "SEP", "OCT", "NOV", "DEC"), 1)}
    for item in months:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("date") or "").strip().upper()
        match = re.fullmatch(r"(\d{4})-(\d{2})(?:-\d{2})?", raw)
        if match:
            year, month = int(match[1]), int(match[2])
        else:
            match = re.fullmatch(r"(\d{4})\s+([A-Z]{3})", raw)
            if not match or match[2] not in month_names:
                continue
            year, month = int(match[1]), month_names[match[2]]
        if not 1 <= month <= 12:
            continue
        try:
            value = float(item["value"])
        except (KeyError, ValueError, TypeError):
            continue
        if math.isfinite(value):
            observations[f"{year:04d}-{month:02d}"] = value
    return sorted(observations.items())


def fetch_ons_cpi():
    request = Request(ONS_CPI_URL, headers={
        "User-Agent": "EarnWage/0.6 (ONS public CPI series)",
        "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return decode_ons_cpi(json.load(response))


def fetch(country, spec):
    if country == "GB":
        if spec["dataset"] == "prc_hicp_minr":
            return fetch_ons_cpi()
        if spec["dataset"] == "earn_nt_net":
            return list(OECD_UK_NET_GBP)
        # Attempt the exact Eurostat household PLI selection for GB, preserving
        # its original EU27=100 methodology; missing years remain unavailable.
    request = Request(source_url(country, spec),
                      headers={"User-Agent": "EarnWage/0.6 (Eurostat public data)",
                               "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return decode(payload, country, spec)


def run(countries, pause=1.0):
    if not countries or len(countries) > 2 or any(
            country not in EUROSTAT_COUNTRIES for country in countries):
        raise ValueError("Choose one or two supported countries")
    totals = {"available": 0, "empty": 0, "failed": 0}
    with connect() as db:
        ensure_tables(db)
        for country in countries:
            for name, spec in SERIES.items():
                try:
                    observations = fetch(country, spec)
                    status = "available" if observations else "empty"
                    error = None
                except (HTTPError, URLError, TimeoutError, ValueError,
                        KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
                    observations, status, error = [], "failed", type(exc).__name__
                save(db, country, name, observations, status, error)
                totals[status] += 1
                print(country, name, status,
                      observations[-1][0] if observations else "-", error or "",
                      flush=True)
                time.sleep(pause)
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", choices=EUROSTAT_COUNTRIES)
    parser.add_argument("--pair", nargs=2, choices=EUROSTAT_COUNTRIES)
    args = parser.parse_args(argv)
    if args.country and args.pair:
        parser.error("Choose --country or --pair")
    if not args.country and not args.pair:
        parser.error("Supply --country or --pair; keep requests batched")
    totals = run((args.country,) if args.country else args.pair)
    print("Summary:", totals, flush=True)
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())

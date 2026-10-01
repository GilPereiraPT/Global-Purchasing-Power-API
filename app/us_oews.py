"""Complete offline importer/query layer for official US BLS OEWS releases.

The importer is deliberately CLI/offline. It accepts the official OEWS "All data"
ZIP/XLSX downloaded from BLS and stores one normalized row per published
occupation/geography/industry observation. Missing/suppressed BLS values remain
NULL; no wage is inferred or annualized.

May 2025 official release catalogue:
https://www.bls.gov/oes/tables.htm
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable
from itertools import chain

import httpx
from openpyxl import load_workbook

from app.store import connect

BLS_TABLE = "https://www.bls.gov/oes/tables.htm"
BLS_2025_ALL_ZIP = "https://www.bls.gov/oes/special-requests/oesm25all.zip"
DEFAULT_YEAR = 2025
MAX_DOWNLOAD_BYTES = 450_000_000
MAX_UNCOMPRESSED_BYTES = 1_500_000_000

# Fields published by recent OEWS downloadable workbooks. The parser tolerates
# additional columns but never silently substitutes another field for these.
IDENTITY_FIELDS = (
    "AREA", "AREA_TITLE", "AREA_TYPE", "PRIM_STATE", "NAICS", "NAICS_TITLE",
    "I_GROUP", "OWN_CODE", "OCC_CODE", "OCC_TITLE", "O_GROUP",
)
NUMERIC_FIELDS = (
    "TOT_EMP", "EMP_PRSE", "JOBS_1000", "LOC_QUOTIENT",
    "PCT_TOTAL", "PCT_RPT", "H_MEAN", "A_MEAN", "MEAN_PRSE",
    "H_PCT10", "H_PCT25", "H_MEDIAN", "H_PCT75", "H_PCT90",
    "A_PCT10", "A_PCT25", "A_MEDIAN", "A_PCT75", "A_PCT90",
)
WAGE_FIELDS = (
    "H_MEAN", "A_MEAN", "H_PCT10", "H_PCT25", "H_MEDIAN",
    "H_PCT75", "H_PCT90", "A_PCT10", "A_PCT25", "A_MEDIAN",
    "A_PCT75", "A_PCT90",
)


def init(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS us_oews (
        reference_period TEXT NOT NULL,
        published_year INTEGER NOT NULL,
        source_file TEXT NOT NULL,
        area TEXT NOT NULL DEFAULT '',
        area_title TEXT NOT NULL DEFAULT '',
        area_type TEXT NOT NULL DEFAULT '',
        prim_state TEXT NOT NULL DEFAULT '',
        naics TEXT NOT NULL DEFAULT '',
        naics_title TEXT NOT NULL DEFAULT '',
        i_group TEXT NOT NULL DEFAULT '',
        own_code TEXT NOT NULL DEFAULT '',
        occ_code TEXT NOT NULL,
        occ_title TEXT NOT NULL,
        o_group TEXT NOT NULL DEFAULT '',
        tot_emp REAL, emp_prse REAL, jobs_1000 REAL, loc_quotient REAL,
        pct_total REAL, pct_rpt REAL,
        h_mean REAL, a_mean REAL, mean_prse REAL,
        h_pct10 REAL, h_pct25 REAL, h_median REAL, h_pct75 REAL, h_pct90 REAL,
        a_pct10 REAL, a_pct25 REAL, a_median REAL, a_pct75 REAL, a_pct90 REAL,
        source_url TEXT NOT NULL,
        PRIMARY KEY (
            reference_period, source_file, area, area_type, prim_state,
            naics, i_group, own_code, occ_code
        )
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_us_oews_occ ON us_oews(occ_code, published_year)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_us_oews_title ON us_oews(occ_title)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_us_oews_geo ON us_oews(area_type, prim_state, area)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_us_oews_scope ON us_oews(naics, own_code, o_group)")


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _number(value):
    if value is None or value == "":
        return None
    text = str(value).strip().replace(",", "")
    # BLS commonly uses *, **, # for unavailable/suppressed/not applicable.
    if text in {"*", "**", "#", "~", "-", "—", "N/A", "NA"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _headers(row) -> list[str]:
    return [_text(value).upper() for value in row]


def _looks_like_data_sheet(headers: list[str]) -> bool:
    required = {"OCC_CODE", "OCC_TITLE"}
    return required <= set(headers) and bool(set(WAGE_FIELDS) & set(headers))


def workbook_records(path: str | Path, year: int = DEFAULT_YEAR) -> Iterable[dict]:
    """Yield normalized rows from every compatible worksheet in an OEWS XLSX."""
    if not 1997 <= year <= 2100:
        raise ValueError("Invalid OEWS year")
    wb = load_workbook(path, read_only=True, data_only=True)
    emitted = 0
    try:
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            try:
                first = next(rows)
            except StopIteration:
                continue
            headers = _headers(first)
            if not _looks_like_data_sheet(headers):
                # Some workbooks put notes/title rows before the real header.
                found = False
                for _ in range(20):
                    try:
                        candidate = next(rows)
                    except StopIteration:
                        break
                    headers = _headers(candidate)
                    if _looks_like_data_sheet(headers):
                        found = True
                        break
                if not found:
                    continue
            for values in rows:
                raw = dict(zip(headers, values))
                occ_code = _text(raw.get("OCC_CODE"))
                occ_title = _text(raw.get("OCC_TITLE"))
                if not re.fullmatch(r"\d{2}-\d{4}", occ_code) or not occ_title:
                    continue
                record = {
                    "reference_period": f"May {year}",
                    "published_year": year,
                    "source_file": Path(path).name + (f":{ws.title}" if len(wb.worksheets) > 1 else ""),
                    "area": _text(raw.get("AREA")),
                    "area_title": _text(raw.get("AREA_TITLE")),
                    "area_type": _text(raw.get("AREA_TYPE")),
                    "prim_state": _text(raw.get("PRIM_STATE")),
                    "naics": _text(raw.get("NAICS")),
                    "naics_title": _text(raw.get("NAICS_TITLE")),
                    "i_group": _text(raw.get("I_GROUP")),
                    "own_code": _text(raw.get("OWN_CODE")),
                    "occ_code": occ_code,
                    "occ_title": occ_title,
                    "o_group": _text(raw.get("O_GROUP")),
                    **{name.lower(): _number(raw.get(name)) for name in NUMERIC_FIELDS},
                    "source_url": BLS_TABLE,
                }
                if not any(record[name.lower()] is not None for name in WAGE_FIELDS):
                    continue
                emitted += 1
                yield record
    finally:
        wb.close()
    if emitted == 0:
        raise ValueError(f"No compatible detailed OEWS rows found in {path}")


DB_COLUMNS = (
    "reference_period", "published_year", "source_file",
    "area", "area_title", "area_type", "prim_state",
    "naics", "naics_title", "i_group", "own_code",
    "occ_code", "occ_title", "o_group",
    *tuple(name.lower() for name in NUMERIC_FIELDS),
    "source_url",
)


def persist(records: Iterable[dict], replace_year: int | None = None) -> int:
    """Stream normalized OEWS rows into SQLite without retaining the release in RAM."""
    iterator = iter(records)
    try:
        first = next(iterator)
    except StopIteration:
        raise ValueError("No OEWS observations; refusing empty import")
    with connect() as db:
        init(db)
        if replace_year is not None:
            db.execute("DELETE FROM us_oews WHERE published_year=?", (replace_year,))
        placeholders = ",".join("?" for _ in DB_COLUMNS)
        sql = f"INSERT OR REPLACE INTO us_oews ({','.join(DB_COLUMNS)}) VALUES ({placeholders})"
        count = 0
        batch = []
        for row in chain((first,), iterator):
            batch.append(tuple(row.get(column) for column in DB_COLUMNS))
            if len(batch) >= 5000:
                db.executemany(sql, batch)
                count += len(batch)
                batch.clear()
        if batch:
            db.executemany(sql, batch)
            count += len(batch)
        db.commit()
    return count


def _safe_zip_members(zf: zipfile.ZipFile):
    total = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("Unsafe path in OEWS ZIP")
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("OEWS ZIP expands beyond safety limit")
        if name.lower().endswith(".xlsx"):
            yield info


def import_zip(path: str | Path, year: int = DEFAULT_YEAR, replace_year: bool = True) -> dict:
    """Import every compatible XLSX member from the official OEWS All-data ZIP."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    imported_files = []
    count = 0
    replaced = False
    with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory(prefix="earnwage-oews-") as tmp:
        members = list(_safe_zip_members(zf))
        if not members:
            raise ValueError("OEWS ZIP contains no XLSX workbooks")
        for info in members:
            target = Path(tmp) / Path(info.filename).name
            with zf.open(info) as src, target.open("wb") as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            records = workbook_records(target, year)
            try:
                imported = persist(records, year if replace_year and not replaced else None)
            except ValueError as exc:
                if "No compatible detailed OEWS rows" in str(exc) or "No OEWS observations" in str(exc):
                    continue
                raise
            count += imported
            replaced = replaced or replace_year
            imported_files.append(info.filename)
    if count == 0:
        raise ValueError("No compatible OEWS workbooks found in ZIP")
    return {
        "status": "imported",
        "published_year": year,
        "reference_period": f"May {year}",
        "rows": count,
        "workbooks": imported_files,
        "source_url": BLS_TABLE,
    }


def download_zip(url: str = BLS_2025_ALL_ZIP) -> Path:
    """Download an official BLS ZIP for CLI use; callers must delete returned file."""
    with httpx.stream("GET", url, timeout=120, follow_redirects=True,
                      headers={"User-Agent": "EarnWage/0.6 OEWS importer"}) as response:
        response.raise_for_status()
        length = response.headers.get("content-length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError("OEWS download exceeds safety limit")
        handle = tempfile.NamedTemporaryFile(prefix="earnwage-oews-", suffix=".zip", delete=False)
        total = 0
        with handle:
            for chunk in response.iter_bytes(1024 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError("OEWS download exceeds safety limit")
                handle.write(chunk)
    return Path(handle.name)


def catalogue(q: str | None = None, limit: int = 100, offset: int = 0):
    term = (q or "").strip().casefold()
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    with connect() as db:
        init(db)
        where = """
            WHERE o_group='detailed'
              AND (area IN ('99','99.0') OR area_title='U.S.')
              AND (naics IN ('000000','0','') OR naics_title IN ('Cross-industry','All Industries',''))
        """
        args = []
        if term:
            where += " AND (lower(occ_title) LIKE ? OR lower(occ_code) LIKE ?)"
            like = f"%{term}%"
            args.extend([like, like])
        rows = db.execute(
            f"""SELECT occ_code,occ_title,MAX(published_year)
                FROM us_oews {where}
                GROUP BY occ_code,occ_title ORDER BY occ_title LIMIT ? OFFSET ?""",
            (*args, limit, offset),
        ).fetchall()
    return {
        "status": "available" if rows else "unavailable",
        "count": len(rows),
        "offset": offset,
        "limit": limit,
        "occupations": [
            {"soc": code, "title": title, "latest_year": year}
            for code, title, year in rows
        ],
        "source_url": BLS_TABLE,
    }


def wages(soc: str, state: str | None = None, area: str | None = None, year: int | None = None):
    if not re.fullmatch(r"\d{2}-\d{4}", soc):
        raise ValueError("Invalid SOC code")
    clauses = ["occ_code=?"]
    args: list[object] = [soc]
    if state:
        clauses.append("prim_state=?")
        args.append(state.upper())
    if area:
        clauses.append("area=?")
        args.append(area)
    if year:
        clauses.append("published_year=?")
        args.append(year)
    where = " AND ".join(clauses)
    with connect() as db:
        init(db)
        rows = db.execute(
            f"""SELECT {','.join(DB_COLUMNS)} FROM us_oews
                WHERE {where}
                ORDER BY published_year DESC,
                  CASE WHEN area IN ('99','99.0') OR area_title='U.S.' THEN 0 ELSE 1 END,
                  area_title,naics_title""",
            tuple(args),
        ).fetchall()
    if not rows:
        return {"status": "unavailable", "soc": soc,
                "reason": "No imported OEWS observation for requested scope"}
    observations = [dict(zip(DB_COLUMNS, row)) for row in rows]
    return {
        "status": "available",
        "soc": soc,
        "title": observations[0]["occ_title"],
        "count": len(observations),
        "observations": observations,
        "note": "Values are BLS-published gross wage statistics. Suppressed/missing values remain null; no annualization or geographic inference.",
    }


def curated_national(soc: str):
    """Return the latest national cross-industry detailed row for one SOC code."""
    if not re.fullmatch(r"\d{2}-\d{4}", soc):
        raise ValueError("Invalid SOC code")
    with connect() as db:
        init(db)
        row = db.execute(
            f"""SELECT {','.join(DB_COLUMNS)} FROM us_oews
                WHERE occ_code=? AND o_group='detailed'
                  AND (area IN ('99','99.0') OR area_title='U.S.')
                  AND (naics IN ('000000','0','') OR naics_title IN ('Cross-industry','All Industries',''))
                ORDER BY published_year DESC LIMIT 1""",
            (soc,),
        ).fetchone()
    return dict(zip(DB_COLUMNS, row)) if row else None


def curated_wage_observations(soc: str):
    """Convert one OEWS national row to the stable EarnWage observation shape."""
    row = curated_national(soc)
    if not row:
        return []
    result = []
    for measure, annual, hourly in (
        ("mean", "a_mean", "h_mean"),
        ("median", "a_median", "h_median"),
    ):
        value = row.get(annual)
        unit = "USD/year"
        if value is None:
            value = row.get(hourly)
            unit = "USD/hour"
        if value is None:
            continue
        result.append({
            "geography": "national",
            "classification": f"SOC2018:{soc}",
            "job_title": row["occ_title"],
            "reference_period": row["reference_period"],
            "published_year": row["published_year"],
            "currency": "USD",
            "measure": measure,
            "unit": unit,
            "value": value,
            "source": f"BLS {row['reference_period']} OEWS national",
            "source_url": row["source_url"],
        })
    return result


def curated_state(soc: str, state: str):
    """Latest exact state-wide, all-industry OEWS record, never a metro proxy."""
    from app.client_config import REGIONS
    valid = {code for code, _ in REGIONS["US"]["options"]}
    if not re.fullmatch(r"\d{2}-\d{4}", soc):
        raise ValueError("Invalid SOC code")
    state = state.upper()
    if state not in valid:
        raise ValueError("Unknown US state")
    with connect() as db:
        init(db)
        rows = db.execute(
            f"""SELECT {','.join(DB_COLUMNS)} FROM us_oews
                WHERE occ_code=? AND prim_state=? AND area_type IN ('2','2.0')
                  AND o_group='detailed'
                  AND naics IN ('000000','0')
                  AND (i_group IN ('cross-industry','cross_industry','') OR i_group IS NULL)
                  AND own_code IN ('1235','')
                ORDER BY published_year DESC, source_file""",
            (soc, state),
        ).fetchall()
    if not rows:
        return None
    latest = max(row[1] for row in rows)
    latest_rows = [dict(zip(DB_COLUMNS, row)) for row in rows if row[1] == latest]
    # Multiple nonidentical official records in the same scope are ambiguous.
    signatures = {(r["area"], r["area_title"], r["a_mean"], r["a_median"],
                   r["h_mean"], r["h_median"]) for r in latest_rows}
    return latest_rows[0] if len(signatures) == 1 else None


def curated_state_wages(occupation: str, state: str):
    """Optional state context; absence never silently falls back to national."""
    from app.north_america import US_SOC, US_SOC_UNMAPPED
    from app.client_config import REGIONS
    state = state.upper()
    names = dict(REGIONS["US"]["options"])
    if state not in names:
        raise ValueError("Unknown US state")
    mapping = US_SOC.get(occupation)
    if not mapping:
        return {"status": "unavailable", "occupation": occupation,
                "state": state, "state_name": names[state],
                "reason": US_SOC_UNMAPPED.get(occupation, "No exact SOC mapping")}
    soc, _ = mapping
    record = curated_state(soc, state)
    if record is None:
        return {"status": "unavailable", "occupation": occupation,
                "state": state, "state_name": names[state],
                "soc": soc, "reason": "No unique, validated state-wide OEWS row imported"}
    metrics = {
        name: record[name] for name in
        ("h_mean", "a_mean", "h_pct10", "h_pct25", "h_median", "h_pct75",
         "h_pct90", "a_pct10", "a_pct25", "a_median", "a_pct75", "a_pct90")
    }
    return {
        "status": "available", "country": "US", "state": state,
        "state_name": names[state], "occupation": occupation, "soc": soc,
        "soc_title": record["occ_title"], "area_title": record["area_title"],
        "scope": "state_wide_cross_industry", "geography": "state",
        "currency": "USD", "reference_period": record["reference_period"],
        "published_year": record["published_year"],
        "hourly_unit": "USD/hour", "annual_unit": "USD/year",
        "metrics": metrics, "source_url": record["source_url"],
        "note": "State-wide BLS occupational wage statistics, not a city wage or a take-home salary. Missing metrics are null.",
    }


def coverage():
    with connect() as db:
        init(db)
        row = db.execute("""SELECT COUNT(*),COUNT(DISTINCT occ_code),
            COUNT(DISTINCT CASE WHEN prim_state<>'' THEN prim_state END),
            MIN(published_year),MAX(published_year) FROM us_oews""").fetchone()
    return {
        "rows": row[0], "occupations": row[1], "states_or_territories": row[2],
        "min_year": row[3], "max_year": row[4], "source_url": BLS_TABLE,
    }


def main():
    parser = argparse.ArgumentParser(description="Import the complete official BLS OEWS release")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--zip", metavar="FILE", help="Official oesmYYall.zip already downloaded")
    source.add_argument("--xlsx", metavar="FILE", help="Single official OEWS workbook")
    source.add_argument("--download", action="store_true", help="Download current May 2025 All-data ZIP from BLS")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--append", action="store_true", help="Do not replace existing rows for the selected year")
    args = parser.parse_args()

    temporary = None
    try:
        if args.download:
            temporary = download_zip()
            result = import_zip(temporary, args.year, not args.append)
        elif args.zip:
            result = import_zip(args.zip, args.year, not args.append)
        else:
            rows = list(workbook_records(args.xlsx, args.year))
            result = {
                "status": "imported",
                "rows": persist(rows, args.year if not args.append else None),
                "published_year": args.year,
                "reference_period": f"May {args.year}",
                "source_url": BLS_TABLE,
            }
        print(json.dumps(result, ensure_ascii=False))
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

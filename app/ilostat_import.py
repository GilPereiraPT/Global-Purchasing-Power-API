"""Reproducible ILOSTAT catalogue CSV / dataset RDS ingestion. Admin CLI only.

Only actual reported values and documented periods are saved. Sex-total, ISCO-08
exact 4-digit, monthly earnings, local-currency observations are admitted.
Unknown classifications, non-total sex, or ambiguous currency are excluded.
"""
import argparse
import csv
import io
import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import httpx

from app.catalog import COUNTRY_MAP
from app.occupations import ISCO08_EXACT
from app.store import connect

BULK = "https://rplumber.ilo.org/files/indicator"
TOC = "https://rplumber.ilo.org/files/indicator/table_of_contents_en.rds"
MAX_COMPRESSED = 35 * 1024 * 1024
MAX_EXPANDED = 180 * 1024 * 1024
COUNTRY_ISO3 = {
    "PT": "PRT", "ES": "ESP", "DE": "DEU", "FR": "FRA",
    "GB": "GBR", "IN": "IND", "BR": "BRA", "PK": "PAK",
    "NL": "NLD", "CH": "CHE", "IT": "ITA", "IE": "IRL",
    "US": "USA", "CA": "CAN",
}
CODE_TO_JOB = {v: k for k, v in ISCO08_EXACT.items() if v}
ISCO_RE = re.compile(r"(?:^|_)ISCO08_([0-9]{4})$")
YEAR_RE = re.compile(r"^[12][0-9]{3}$")


def init_salary_db(db):
    db.execute("""CREATE TABLE IF NOT EXISTS salary_observations (
        country TEXT NOT NULL, occupation TEXT NOT NULL, period TEXT NOT NULL,
        indicator TEXT NOT NULL, source_code TEXT NOT NULL,
        classification TEXT NOT NULL, currency TEXT NOT NULL,
        value REAL NOT NULL, dataset TEXT NOT NULL, source_url TEXT NOT NULL,
        PRIMARY KEY(country,occupation,period,indicator,source_code,classification,currency)
    )""")


def read_rds_frame(payload, max_bytes=MAX_EXPANDED):
    """Read only an official R data frame; reject unexpected formats."""
    import pyreadr
    if len(payload) > max_bytes:
        raise ValueError("Official RDS exceeds configured size limit")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "official.rds"
        path.write_bytes(payload)
        objects = pyreadr.read_r(str(path))
    if len(objects) != 1:
        raise ValueError("Unexpected RDS object count")
    frame = next(iter(objects.values()))
    if frame is None or frame.empty:
        raise ValueError("Empty official RDS data frame")
    return frame


def catalogue_rows():
    """Use the official Rilostat bulk TOC transport (.rds), not CSV over an API route."""
    frame = read_rds_frame(download(TOC, 10_000_000))
    required = {"id", "indicator.label"}
    if not required <= set(frame.columns):
        raise ValueError("ILOSTAT catalogue schema mismatch: " + repr(list(frame.columns)))
    return frame.fillna("").to_dict(orient="records")


def earnings_datasets(rows):
    """Select ONLY occupation-specific employee monthly earning datasets."""
    out = []
    for row in rows:
        label = row.get("indicator.label", "").lower()
        dataset = row.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_]+_A", dataset):
            continue
        if ("average monthly earnings" in label and "occupation" in label
                and "employees" in label and "sex" in label
                and ("local currency" in label or "currency" in label)):
            out.append({"id": dataset, "label": row.get("indicator.label"),
                        "last_update": row.get("last.update"),
                        "period_end": row.get("data.end")})
    return out


def parse_row(row, dataset, dataset_label):
    country = next((k for k, v in COUNTRY_ISO3.items()
                    if v == row.get("ref_area")), None)
    if country is None or row.get("sex") != "SEX_T":
        return None
    if not YEAR_RE.fullmatch(row.get("time", "")):
        return None
    # ILO classification is explicitly ISCO-08. Different classification
    # editions, country-specific groups and 1/2/3-digit groups are NOT mapped.
    match = ISCO_RE.search(row.get("classif1", ""))
    if not match or match.group(1) not in CODE_TO_JOB:
        return None
    label = dataset_label.lower()
    currency_code = COUNTRY_MAP[country]["currency"]
    # Annual ILOSTAT datasets can include multiple currencies/PPPs.
    # Only declared local currency can be treated as national-currency salary.
    if row.get("classif2") not in ("CUR_LCU", "CUR_NCU", "CUR_TYPE_LCU"):
        return None
    try:
        value = float(row["obs_value"])
    except (KeyError, ValueError, TypeError):
        return None
    if not (0 < value < 1e12):
        return None
    return (
        country, CODE_TO_JOB[match.group(1)], row["time"],
        row.get("indicator", dataset.removesuffix("_A")),
        row.get("source", "unspecified"), row["classif1"],
        currency_code, value, dataset, f"{BULK}/{dataset}.rds",
    )


def import_csv(db, text, dataset, label):
    init_salary_db(db)
    if not ("average monthly earnings" in label.lower() and "occupation" in label.lower() and "employees" in label.lower()):
        raise ValueError("Only average monthly earnings datasets are supported")
    if not re.fullmatch(r"[A-Za-z0-9_]+_A", dataset):
        raise ValueError("Invalid annual dataset id")
    count = 0
    reader = csv.DictReader(io.StringIO(text))
    required = {"ref_area", "sex", "classif1", "time", "obs_value", "source"}
    if not required <= set(reader.fieldnames or []):
        raise ValueError("Unexpected ILOSTAT data columns; refusing import")
    for row in reader:
        observation = parse_row(row, dataset, label)
        if observation:
            db.execute("""INSERT OR REPLACE INTO salary_observations
                (country,occupation,period,indicator,source_code,classification,
                 currency,value,dataset,source_url)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", observation)
            count += 1
    if count == 0:
        raise ValueError("No eligible observations; inspect official source schema and filters")
    db.commit()
    return count


def salary(country, occupation):
    with connect() as db:
        init_salary_db(db)
        rows = db.execute("""SELECT period, indicator, source_code, classification,
               currency, value, dataset, source_url FROM salary_observations
               WHERE country=? AND occupation=? ORDER BY period DESC,source_code""",
               (country, occupation)).fetchall()
    if not rows:
        return {"status": "unavailable", "reason": "No matching imported ISCO-08 exact observation",
                "country": country, "occupation": occupation, "geography": "national"}
    latest = rows[0][0]
    current = [r for r in rows if r[0] == latest]
    if len(current) != 1:
        return {"status": "ambiguous", "reason": "Multiple source observations for latest year; choose a source explicitly",
                "country": country, "occupation": occupation, "latest_period": latest,
                "sources": [r[2] for r in current]}
    period, indicator, source, classification, currency, value, dataset, url = current[0]
    return {"status": "available", "country": country, "occupation": occupation,
            "value": value, "currency": currency, "period": period,
            "unit": "monthly gross earnings (as reported by ILOSTAT dataset)",
            "geography": "national", "classification": classification,
            "precision": "exact_occupation_isco08", "source": "ILOSTAT",
            "source_code": source, "indicator": indicator, "dataset": dataset,
            "source_url": url, "note": "Not a capital-city salary or an individual salary offer."}


def availability():
    """All occupations x all countries: strictly observed, never estimated."""
    with connect() as db:
        init_salary_db(db)
        rows = db.execute("""SELECT country,occupation,MAX(period)
                             FROM salary_observations GROUP BY country,occupation""").fetchall()
    observed = {(country, job): period for country, job, period in rows}
    from app.catalog import OCCUPATIONS
    return {
        "countries": len(COUNTRY_MAP), "occupations": len(OCCUPATIONS),
        "cells": [
            {"country": code, "occupation": job["id"],
             "status": "available" if (code, job["id"]) in observed else "unavailable",
             "latest_period": observed.get((code, job["id"]))}
            for code in COUNTRY_MAP for job in OCCUPATIONS
        ],
    }


def download(url, max_bytes=MAX_COMPRESSED):
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Source download exceeds configured size limit")
                chunks.append(chunk)
            return b"".join(chunks)


def import_rds(db, payload, dataset, label):
    """Read the official RDS data frame without accepting fabricated CSV fallbacks."""
    frame = read_rds_frame(payload, MAX_COMPRESSED)
    required = {"ref_area", "sex", "classif1", "time", "obs_value", "source"}
    if not required <= set(frame.columns):
        raise ValueError("Unexpected ILOSTAT RDS columns; refusing import")
    # Preserve the existing strict CSV validation and row-level exclusion rules.
    text = frame.to_csv(index=False)
    if len(text.encode("utf-8")) > MAX_EXPANDED:
        raise ValueError("Expanded source exceeds configured size limit")
    return import_csv(db, text, dataset, label)


def run(dataset, label=None):
    toc_rows = catalogue_rows()
    candidates = {x["id"]: x for x in earnings_datasets(toc_rows)}
    if dataset not in candidates:
        raise ValueError("Dataset is absent from official earnings-by-occupation annual catalogue")
    known = candidates[dataset]
    if label and label != known["label"]:
        raise ValueError("Dataset label does not match official catalogue")
    payload = download(f"{BULK}/{dataset}.rds")
    with connect() as db:
        inserted = import_rds(db, payload, dataset, known["label"])
    return {"dataset": dataset, "eligible_rows_imported": inserted,
            "source": f"{BULK}/{dataset}.rds",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "official_last_update": known["last_update"]}


def export_snapshot(path="data/salaries_snapshot.json"):
    """Publish source-backed observations as JSON for GitHub-to-host deployment."""
    from app.catalog import OCCUPATIONS
    with connect() as db:
        init_salary_db(db)
        rows = db.execute("""SELECT country,occupation,period,indicator,source_code,
              classification,currency,value,dataset,source_url
              FROM salary_observations ORDER BY country,occupation,period,source_code""").fetchall()
    if not rows:
        raise ValueError("No ILOSTAT observations imported; refusing empty snapshot")
    columns = ["country","occupation","period","indicator","source_code",
               "classification","currency","value","dataset","source_url"]
    payload = {"schema_version": 1, "source": "ILOSTAT", "observations":
               [dict(zip(columns, r)) for r in rows]}
    from pathlib import Path
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(destination), "observations": len(rows)}


def load_snapshot(path="data/salaries_snapshot.json"):
    """Load only vetted snapshot records; no data returned if snapshot absent."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return 0
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("source") != "ILOSTAT":
        raise ValueError("Unsupported salary snapshot")
    records = data.get("observations", [])
    if not isinstance(records, list):
        raise ValueError("Invalid salary snapshot")
    with connect() as db:
        init_salary_db(db)
        for row in records:
            country, occupation = row["country"], row["occupation"]
            if country not in COUNTRY_MAP or ISCO08_EXACT.get(occupation) is None:
                raise ValueError("Unknown country or unmapped occupation in snapshot")
            if row["classification"] != "OCU_ISCO08_" + ISCO08_EXACT[occupation]:
                raise ValueError("Incorrect ISCO-08 mapping in snapshot")
            if row["currency"] != COUNTRY_MAP[country]["currency"]:
                raise ValueError("Incorrect currency in snapshot")
            if not YEAR_RE.fullmatch(row["period"]) or not (0 < float(row["value"]) < 1e12):
                raise ValueError("Invalid year or observation")
            db.execute("""INSERT OR REPLACE INTO salary_observations
                (country,occupation,period,indicator,source_code,classification,
                 currency,value,dataset,source_url)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", tuple(row[k] for k in
                ("country","occupation","period","indicator","source_code",
                 "classification","currency","value","dataset","source_url")))
        db.commit()
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List official eligible annual datasets")
    parser.add_argument("--dataset", help="Validated ILOSTAT annual indicator id")
    parser.add_argument("--export", action="store_true", help="Write source-backed salary JSON snapshot")
    args = parser.parse_args()
    if args.list:
        rows = catalogue_rows()
        found = earnings_datasets(rows)
        print(json.dumps({"catalogue_rows": len(rows),
                          "columns": list(rows[0]) if rows else [],
                          "earnings_candidates": found,
                          "earnings_near_matches": [
                              {"id": row.get("id"), "label": row.get("indicator.label")}
                              for row in rows if "EAR_EMTA" in str(row.get("id", ""))
                          ][:15]}, indent=2, default=str))
    elif args.dataset:
        print(json.dumps(run(args.dataset), indent=2))
    elif args.export:
        print(json.dumps(export_snapshot(), indent=2))
    else:
        parser.error("Provide --list, --dataset DATASET_ID, or --export")


if __name__ == "__main__":
    main()

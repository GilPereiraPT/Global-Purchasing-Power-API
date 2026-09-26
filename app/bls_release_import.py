"""Curated 2025 BLS OEWS national RELEASE observations, checked against the
original federal Table 1. Fallback when bulk BLS XLSX access returns HTTP 403.

This is deliberately a *reviewed subset* (annual mean only) rather than claiming
to have downloaded or parsed the complete national spreadsheet.
"""
import argparse
import csv
from pathlib import Path
from app.north_america import (
    US_SOC, BLS_DATASET, BLS_NEWS_TABLE, COLUMNS,
    persist, export_snapshot, load_snapshot
)

ROOT = Path(__file__).resolve().parent.parent
REVIEWED_FILE = ROOT / "data" / "bls_2025_release_reviewed.csv"
SNAPSHOT = ROOT / "data" / "north_america_wages.json"


def reviewed_rows(path=REVIEWED_FILE):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        expected = {"occupation", "soc", "title", "annual_mean_usd", "source_url"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError("Unrecognized reviewed BLS release CSV")
        seen = set()
        for row in reader:
            job = row["occupation"]
            if job in seen or job not in US_SOC:
                raise ValueError("Duplicate or unknown BLS occupation")
            seen.add(job)
            soc, expected_title = US_SOC[job]
            if row["soc"] != soc or row["title"].casefold() != expected_title.casefold():
                raise ValueError("SOC code or official title mismatch")
            if row["source_url"] != BLS_NEWS_TABLE:
                raise ValueError("Source must link to original BLS national 2025 Table 1")
            raw = row["annual_mean_usd"]
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError("Unrecognized annual mean wage format")
            wage = int(raw)
            if not 1 <= wage <= 1000000:
                raise ValueError("Annual mean wage outside accepted range")
            yield (
                "US", job, "national", "SOC2018:" + soc, expected_title,
                "May 2025", 2025, "USD", "mean", "USD/year", wage,
                BLS_DATASET + " (Table 1 reviewed subset)", BLS_NEWS_TABLE
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-file", type=Path, default=REVIEWED_FILE)
    args = parser.parse_args()
    existing = load_snapshot(SNAPSHOT)
    count = persist(reviewed_rows(args.reviewed_file))
    exported = export_snapshot(SNAPSHOT)
    print(f"official BLS 2025 reviewed national mean wage rows: {count}; "
          f"preloaded Canada/US rows: {existing}; exported rows: {exported}")


if __name__ == "__main__":
    main()

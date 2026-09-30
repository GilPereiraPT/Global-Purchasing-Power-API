"""Statistics Canada broad NOC 2021 wage context.

Official annual Labour Force Survey table 14-10-0417-01. These observations
are broad occupational context only and must never be relabelled as an exact
occupation wage.
"""
import csv
import io
import json
import math
import zipfile
from pathlib import Path

TABLE = "14-10-0417-01"
SOURCE = "Statistics Canada"
SOURCE_URL = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701"
DOWNLOAD_URL = "https://www150.statcan.gc.ca/n1/en/tbl/csv/14100417-eng.zip"
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "ca_statcan_groups.json"
YEAR = "2025"

BROAD = {
    "0": "Management occupations",
    "1": "Business, finance and administration occupations, except management",
    "2": "Natural and applied sciences and related occupations",
    "3": "Health occupations",
    "4": "Occupations in education, law and social, community and government services",
    "5": "Occupations in art, culture, recreation and sport",
    "6": "Sales and service occupations",
    "7": "Trades, transport and equipment operators and related occupations",
    "8": "Natural resources, agriculture and related production occupations",
    "9": "Occupations in manufacturing and utilities",
}

# Explicit EarnWage -> NOC broad category context. The 38 exact Canadian NOC
# mappings inherit their first NOC digit; the two intentionally unresolved
# exact occupations still have unambiguous broad-category context.
SPECIAL = {"manager": "0", "agricultural_worker": "8"}


def occupation_groups():
    from app.north_america import CANADA_NOC
    mapping = {occupation: noc[0] for occupation, (noc, _title) in CANADA_NOC.items()}
    mapping.update(SPECIAL)
    return mapping


def _metric(label):
    value = label.strip().lower()
    if value == "average hourly wage rate":
        return "mean_hourly"
    if value == "median hourly wage rate":
        return "median_hourly"
    if value == "average weekly wage rate":
        return "mean_weekly"
    if value == "median weekly wage rate":
        return "median_weekly"
    return None


def build_snapshot(zip_path, year=YEAR):
    records = {}
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")
                 and "metadata" not in n.lower()]
        if not names:
            raise ValueError("Statistics Canada archive has no data CSV")
        # The full-table data CSV is the largest CSV in the archive.
        name = max(names, key=lambda n: archive.getinfo(n).file_size)
        with archive.open(name) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            fields = reader.fieldnames or []
            noc_col = next((f for f in fields if f.startswith("National Occupational Classification")), None)
            if not noc_col:
                raise ValueError("NOC column missing from Statistics Canada table")
            required = {"REF_DATE", "GEO", "Wages", "Type of work", "Gender",
                        "Age group", "VALUE", "UOM"}
            if not required.issubset(fields):
                raise ValueError("Unexpected Statistics Canada table schema")
            for row in reader:
                if (row["REF_DATE"] != str(year) or row["GEO"] != "Canada" or
                    row["Type of work"] != "Both full- and part-time employees" or
                    row["Gender"] != "Total - Gender" or
                    row["Age group"] != "15 years and over"):
                    continue
                title = row[noc_col].strip()
                # Table 14-10-0417-01 exposes the NOC hierarchy as labels,
                # without the numeric NOC code. Match only the ten official
                # broad-category labels so lower-level occupations cannot leak
                # into the group context.
                group = next((g for g, label in BROAD.items() if title == label), None)
                metric = _metric(row["Wages"])
                if group is None or metric is None:
                    continue
                try:
                    value = float(row["VALUE"])
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value) or value <= 0:
                    continue
                key = (group, metric)
                if key in records:
                    raise ValueError("Duplicate Canada broad NOC wage observation")
                records[key] = {
                    "noc2021_broad_category": group,
                    "label": BROAD[group],
                    "measure": metric,
                    "value": value,
                    "currency": "CAD",
                    "unit": "CAD/hour" if metric.endswith("_hourly") else "CAD/week",
                    "reference_period": str(year),
                    "geography": "Canada",
                    "population": "employees age 15+, both full- and part-time, total gender",
                    "precision": "noc2021_broad_category",
                    "source": SOURCE,
                    "table": TABLE,
                    "source_url": SOURCE_URL,
                }
    missing = [g for g in BROAD if not any(k[0] == g for k in records)]
    if missing:
        raise ValueError("Missing broad NOC categories: " + ",".join(missing))
    observations = sorted(records.values(), key=lambda r:(r["noc2021_broad_category"], r["measure"]))
    return {"schema_version": 1, "source": SOURCE, "table": TABLE,
            "reference_period": str(year), "observations": observations}


def save_snapshot(zip_path, output=DEFAULT, year=YEAR):
    snapshot = build_snapshot(zip_path, year)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(snapshot["observations"])


def load_snapshot(path=DEFAULT):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1 or data.get("source") != SOURCE or
        data.get("table") != TABLE or not isinstance(data.get("observations"), list)):
        raise ValueError("Unsupported Statistics Canada broad-group snapshot")
    return data["observations"]


def context(occupation, path=DEFAULT):
    group = occupation_groups().get(occupation)
    if group is None:
        return {"status": "unavailable", "country": "CA",
                "precision": "noc2021_broad_category",
                "reason": "No validated NOC broad-category mapping"}
    rows = [r for r in load_snapshot(path) if r["noc2021_broad_category"] == group]
    if not rows:
        return {"status": "unavailable", "country": "CA",
                "noc2021_broad_category": group, "label": BROAD[group],
                "precision": "noc2021_broad_category"}
    return {"status": "available", "country": "CA",
            "noc2021_broad_category": group, "label": BROAD[group],
            "precision": "noc2021_broad_category",
            "reference_period": max(r["reference_period"] for r in rows),
            "observations": rows, "source": SOURCE, "table": TABLE,
            "source_url": SOURCE_URL,
            "note": "Broad NOC 2021 occupational context; not the selected profession's salary."}


def coverage(path=DEFAULT):
    return {occupation for occupation in occupation_groups()
            if context(occupation, path).get("status") == "available"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--output", default=str(DEFAULT))
    parser.add_argument("--year", default=YEAR)
    args = parser.parse_args()
    print("Eligible Statistics Canada broad-group observations:",
          save_snapshot(args.zip_path, args.output, args.year))

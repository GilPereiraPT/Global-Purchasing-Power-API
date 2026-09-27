"""ILOSTAT national major occupation group earnings; separate from exact jobs.

No inference from ISCO major group to individual occupations. Multiple sources
in a country/year/group/currency remain ambiguous, not silently averaged.
"""
import csv
import json
import math
import re
from pathlib import Path

from app.catalog import COUNTRY_MAP

DATASET = "EAR_EMTA_SEX_OCU_CUR_NB_A"
INDICATOR = "EAR_EMTA_SEX_OCU_CUR_NB"
SOURCE_URL = "https://rplumber.ilo.org/files/indicator/" + DATASET + ".rds"
COUNTRIES = {"PRT":"PT","ESP":"ES","DEU":"DE","FRA":"FR","GBR":"GB",
             "IND":"IN","BRA":"BR","PAK":"PK","NLD":"NL","CHE":"CH",
             "ITA":"IT","IRL":"IE","USA":"US","CAN":"CA"}
UNITS = {"CUR_TYPE_LCU":"local_currency", "CUR_TYPE_USD":"usd",
         "CUR_TYPE_PPP":"ppp"}
GROUP_RE = re.compile(r"^OCU_ISCO08_([1-9])$")
YEAR_RE = re.compile(r"^20[0-9]{2}$")
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "ilostat_group_salaries.json"


def build_snapshot(csv_path):
    """Convert Rilostat's official, unmodified CSV export into a vetted snapshot."""
    records = []
    with open(csv_path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"ref_area","source","indicator","sex","classif1",
                    "classif2","time","obs_value","best_source"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing official ILOSTAT columns")
        for row in reader:
            country = COUNTRIES.get(row["ref_area"])
            match = GROUP_RE.fullmatch(row["classif1"])
            unit = UNITS.get(row["classif2"])
            if (not country or not match or not unit or
                    row["sex"] != "SEX_T" or row["best_source"] != "1" or
                    row["indicator"] != INDICATOR or
                    not YEAR_RE.fullmatch(row["time"])):
                continue
            try:
                value = float(row["obs_value"])
            except (ValueError, TypeError):
                continue
            if not math.isfinite(value) or not 0 < value < 1e12:
                continue
            records.append({
                "country":country, "period":row["time"],
                "isco08_major_group":match.group(1),
                "unit_type":unit,
                "currency": COUNTRY_MAP[country]["currency"] if unit == "local_currency" else None,
                "value":value, "source_code":row["source"],
                "best_source":True,
                "indicator":INDICATOR, "dataset":DATASET,
                "source_url":SOURCE_URL,
                "precision":"isco08_major_group",
                "geography":"national",
                "note":"Published ILOSTAT monthly employee earnings; not an individual occupation salary."
            })
    if not records:
        raise ValueError("No eligible ISCO-08 major-group observations; refusing empty snapshot")
    records.sort(key=lambda r:(r["country"],r["isco08_major_group"],r["period"],
                               r["unit_type"],r["source_code"]))
    return {"schema_version":1, "source":"ILOSTAT", "dataset":DATASET,
            "observations":records}


def save_snapshot(csv_path, output=DEFAULT):
    snapshot = build_snapshot(csv_path)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n",
                      encoding="utf-8")
    return len(snapshot["observations"])


def load_snapshot(path=DEFAULT):
    path = Path(path)
    if not path.exists():
        return []
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if (snapshot.get("schema_version") != 1 or
            snapshot.get("source") != "ILOSTAT" or
            snapshot.get("dataset") != DATASET or
            not isinstance(snapshot.get("observations"), list)):
        raise ValueError("Unsupported ILOSTAT group snapshot")
    return snapshot["observations"]



def group_coverage(path=DEFAULT):
    """Separate coverage: country × ISCO-08 major group, not exact occupations."""
    rows = load_snapshot(path)
    pairs = {(r["country"], r["isco08_major_group"]) for r in rows
             if r.get("unit_type") == "local_currency"}
    by_country = [{"code":code,
                   "observed_groups":sum((code, str(g)) in pairs for g in range(1, 10)),
                   "possible_groups":9}
                  for code in COUNTRY_MAP]
    return {"source":"ILOSTAT", "dataset":DATASET,
            "precision":"isco08_major_group", "observations":len(rows),
            "observed_pairs":len(pairs), "possible_pairs":len(COUNTRY_MAP)*9,
            "by_country":by_country,
            "note":"Group-level observations are NOT salaries for the 40 individual occupations."}


def group_salary(country, group, path=DEFAULT):
    code = country.upper()
    if code not in COUNTRY_MAP or not re.fullmatch("[1-9]", str(group)):
        raise ValueError("Unknown country or ISCO-08 major group")
    rows = [r for r in load_snapshot(path) if r["country"] == code
            and r["isco08_major_group"] == str(group)]
    if not rows:
        return {"status":"unavailable", "country":code,
                "isco08_major_group":str(group), "precision":"isco08_major_group"}
    period = max(r["period"] for r in rows)
    selected = [r for r in rows if r["period"] == period]
    units = {}
    for unit in UNITS.values():
        matches = [r for r in selected if r["unit_type"] == unit]
        if len(matches) == 1:
            units[unit] = {"status":"available", "value":matches[0]["value"],
                           "currency":matches[0]["currency"],
                           "source_code":matches[0]["source_code"]}
        elif len(matches) > 1:
            units[unit] = {"status":"ambiguous",
                           "source_codes":sorted({r["source_code"] for r in matches})}
        else:
            units[unit] = {"status":"unavailable"}
    return {"status":"available", "country":code, "period":period,
            "isco08_major_group":str(group), "precision":"isco08_major_group",
            "geography":"national", "unit":"monthly employee earnings",
            "values":units, "indicator":INDICATOR, "dataset":DATASET,
            "source_url":SOURCE_URL,
            "note":"PPP is the published ILOSTAT series, not an EarnWage purchasing-power calculation. No salary is inferred for an individual occupation."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output", default=str(DEFAULT))
    args = parser.parse_args()
    print("Eligible group salary observations:", save_snapshot(args.csv, args.output))

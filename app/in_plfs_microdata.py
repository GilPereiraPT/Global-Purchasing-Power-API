"""PLFS 2025 first-visit *aggregated* monthly regular employee earnings.

Requires officially obtained person CSV and a separately audited manifest mapping
official State/UT and NCO-2015 codes. No respondent-level data are persisted.
Outputs design-weighted descriptive means, NOT design-based confidence intervals.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from app.in_plfs import MICRODATA_URL
from app.store import connect

REFERENCE_PERIOD = "January–December 2025"
SOURCE = "MoSPI PLFS 2025 calendar-year first-visit person-level microdata"
# This is a conservative product disclosure rule, not a MoSPI official rule.
MIN_SAMPLE = 50
MIN_EFFECTIVE = 30
REQUIRED = {"visit", "st", "sec", "acws", "ocu_cws", "ern_reg", "mult", "mfsu",
            "qtr", "month"}


def validate_manifest(manifest):
    if manifest.get("survey") != "DDI-IND-NSO-PLFS-Jan2025-Dec2025":
        raise ValueError("Wrong survey manifest")
    if manifest.get("official_state_crosswalk_reviewed") is not True:
        raise ValueError("Official State/UT crosswalk has not been reviewed")
    states = manifest.get("states")
    if not isinstance(states, dict) or not states:
        raise ValueError("Official State/UT crosswalk missing")
    if not all(re.fullmatch(r"\d{1,4}", k) and isinstance(v, str) and v.strip()
               for k, v in states.items()):
        raise ValueError("Invalid official state codes")
    codes = manifest.get("occupations")
    if not isinstance(codes, dict) or not codes:
        raise ValueError("No reviewed NCO-2015 occupation codes")
    if not all(re.fullmatch(r"\d{3,8}", k) and
               isinstance(v, str) and v.strip() for k, v in codes.items()):
        raise ValueError("Invalid audited NCO-2015 occupation labels")
    if manifest.get("first_visit_code") not in ("1", 1):
        raise ValueError("First visit code must be verified as 1")
    if manifest.get("regular_employee_cws_codes") != ["31", "71", "72"]:
        raise ValueError("Expected PLFS salaried CWS codes [31,71,72]")
    if manifest.get("multiplier_scale") != 100:
        raise ValueError("2025 first-visit multiplier convention must be /100")
    if manifest.get("verified_person_file") != "cperv12025":
        raise ValueError("Only official first-visit person file is supported")
    return states, codes


def aggregate(csv_file, manifest):
    """Stream one official UTF-8 person CSV; fail closed on incompatible schema."""
    states, occupations = validate_manifest(manifest)
    stats = defaultdict(lambda: [0, 0., 0., 0., set()])
    diagnostics = {"rows_read": 0, "eligible_regular_employees": 0,
                   "mapped_eligible": 0, "missing_earnings": 0,
                   "unknown_states": set(), "unknown_occupations": set()}
    with open(csv_file, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Unexpected PLFS 2025 first-visit CSV columns")
        for row in reader:
            diagnostics["rows_read"] += 1
            if row["visit"].strip() != "1" or row["acws"].strip() not in ("31", "71", "72"):
                continue
            diagnostics["eligible_regular_employees"] += 1
            state, occupation = row["st"].strip().lstrip("0") or "0", row["ocu_cws"].strip()
            if state not in states:
                diagnostics["unknown_states"].add(state)
                continue
            if occupation not in occupations:
                diagnostics["unknown_occupations"].add(occupation)
                continue
            try:
                pay = float(row["ern_reg"])
                weight = float(row["mult"]) / 100
            except (TypeError, ValueError):
                diagnostics["missing_earnings"] += 1
                continue
            # A zero-month amount is meaningful and must not be dropped.
            if not math.isfinite(pay) or not 0 <= pay <= 100_000_000 or not math.isfinite(weight) or weight <= 0:
                diagnostics["missing_earnings"] += 1
                continue
            fsu = row["mfsu"].strip()
            if not fsu:
                raise ValueError("Person record without first-stage sampling unit")
            diagnostics["mapped_eligible"] += 1
            for scope in ("national", state):
                cell = stats[(occupation, scope)]
                cell[0] += 1
                cell[1] += weight
                cell[2] += weight * weight
                cell[3] += weight * pay
                # Conservative sampling-cluster approximation.
                cell[4].add((row["qtr"], row["month"], state, row["sec"], fsu))
    public = []
    suppressed = 0
    for (occupation, scope), (n, sw, sw2, swpay, psu) in sorted(stats.items()):
        effective = sw * sw / sw2 if sw2 else 0
        if n < MIN_SAMPLE or effective < MIN_EFFECTIVE or len(psu) < 10:
            suppressed += 1
            continue
        public.append({
            "nco2015_code": occupation, "nco2015_label": occupations[occupation],
            "geography": "national" if scope == "national" else "state",
            "state_code": None if scope == "national" else scope,
            "state_name": None if scope == "national" else states[scope],
            "mean_monthly_earnings": round(swpay / sw, 2),
            "sample_n": n, "effective_n_approx": round(effective, 1),
            "observed_psu_count_approx": len(psu),
            "currency": "INR", "unit": "INR/month",
            "population": "CWS regular salaried/wage employees",
            "measure": "survey_weighted_mean_preceding_calendar_month",
            "precision": "audited_nco2015_code",
            "period": REFERENCE_PERIOD, "source": SOURCE,
            "source_url": MICRODATA_URL,
        })
    diagnostics["unknown_states"] = sorted(diagnostics["unknown_states"])
    diagnostics["unknown_occupations"] = sorted(diagnostics["unknown_occupations"])
    diagnostics["suppressed_cells"] = suppressed
    diagnostics["published_cells"] = len(public)
    return public, diagnostics


def export(csv_file, manifest_path, output="data/in_plfs_2025_nco.json"):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    published, diagnostics = aggregate(csv_file, manifest)
    if not published:
        raise ValueError("No disclosure-safe PLFS occupation/state observations")
    if diagnostics["unknown_states"]:
        raise ValueError("Official state crosswalk incomplete; refusing misleading coverage")
    # Only aggregated results and a checksum of the reviewed manifest are exported.
    manifest_bytes = Path(manifest_path).read_bytes()
    payload = {
        "schema": 1, "survey": manifest["survey"], "period": REFERENCE_PERIOD,
        "population": "CWS regular salaried/wage employees",
        "sampling_note": ("Descriptive weighted means. Effective sample size and unique "
                          "FSU counts are approximate; no design-based standard errors "
                          "or statistical precision guarantees."),
        "reviewed_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_url": MICRODATA_URL,
        "minimum_raw_n": MIN_SAMPLE, "minimum_effective_n": MIN_EFFECTIVE,
        "records": published,
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"published_cells": len(published), "suppressed_cells": diagnostics["suppressed_cells"],
            "source_rows": diagnostics["rows_read"],
            "unknown_nco_codes": len(diagnostics["unknown_occupations"])}


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS in_plfs_nco_wages (
        nco_code TEXT NOT NULL, scope TEXT NOT NULL, state_code TEXT NOT NULL,
        label TEXT NOT NULL, state_name TEXT, value REAL NOT NULL, sample_n INTEGER NOT NULL,
        effective_n REAL NOT NULL, psu_count INTEGER NOT NULL,
        period TEXT NOT NULL, source_url TEXT NOT NULL,
        PRIMARY KEY(nco_code,scope,state_code,period)
    )""")


def load_snapshot(path="data/in_plfs_2025_nco.json"):
    path = Path(path)
    if not path.exists():
        return 0
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != 1 or obj.get("survey") != "DDI-IND-NSO-PLFS-Jan2025-Dec2025":
        raise ValueError("Unexpected PLFS survey snapshot")
    records = obj.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Empty PLFS NCO observations")
    source_kind = obj.get("source_kind", "direct_official_microdata")
    if source_kind not in ("direct_official_microdata", "third_party_preprocessed_official_microdata"):
        raise ValueError("Unknown PLFS dataset provenance")
    if source_kind == "third_party_preprocessed_official_microdata":
        from app.in_plfs_derived_import import SOURCE_SHA256, DERIVATIVE_URL
        if (obj.get("derivative_sha256") != SOURCE_SHA256
                or obj.get("source_url") != DERIVATIVE_URL
                or not obj.get("reuse_license", "").startswith("Open Database License")):
            raise ValueError("Unreviewed PLFS derivative source")
    rows = []
    for item in records:
        code, scope = item["nco2015_code"], item["geography"]
        state = item["state_code"] or ""
        n, neff, psu = item["sample_n"], item["effective_n_approx"], item["observed_psu_count_approx"]
        v = item["mean_monthly_earnings"]
        if (not re.fullmatch(r"\d{3,8}", code) or scope not in ("national", "state")
                or (scope == "national" and state) or (scope == "state" and not state)
                or item["unit"] != "INR/month" or item["period"] != REFERENCE_PERIOD
                or n < MIN_SAMPLE or neff < MIN_EFFECTIVE or psu < 10
                or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0):
            raise ValueError("Invalid or insufficient PLFS result")
        if source_kind == "third_party_preprocessed_official_microdata":
            if (item.get("precision") != "broad_nco2015_three_digit_group"
                    or item.get("source_url") != obj["source_url"]):
                raise ValueError("Derivative NCO group or source mismatch")
        rows.append((code, scope, state, item["nco2015_label"], item["state_name"],
                     v, n, neff, psu, item["period"],
                     item.get("source_url", MICRODATA_URL)))
    with connect() as db:
        init(db)
        db.executemany("INSERT OR REPLACE INTO in_plfs_nco_wages VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return len(rows)


def wages(nco_code, state=None):
    if not re.fullmatch(r"\d{3,8}", nco_code):
        raise ValueError("Invalid NCO-2015 occupation code")
    if state is not None and not re.fullmatch(r"\d{1,4}", state):
        raise ValueError("Invalid official state code")
    with connect() as db:
        init(db)
        row = db.execute("""SELECT label, state_name,value,sample_n,effective_n,
            psu_count,period,source_url FROM in_plfs_nco_wages
            WHERE nco_code=? AND scope=? AND state_code=?""",
            (nco_code, "state" if state is not None else "national", state or "")).fetchone()
    if not row:
        return {"status": "unavailable", "nco2015_code": nco_code, "state_code": state,
                "reason": "No disclosure-safe, reviewed 2025 PLFS observation imported"}
    return {
        "status": "available", "nco2015_code": nco_code, "nco2015_label": row[0],
        "geography": "state" if state is not None else "national",
        "state_code": state, "state_name": row[1], "value": row[2],
        "currency": "INR", "unit": "INR/month",
        "measure": "survey_weighted_mean_preceding_calendar_month",
        "sample_n": row[3], "effective_n_approx": row[4],
        "psu_count_approx": row[5], "reference_period": row[6],
        "source_url": row[7],
        "note": ("NCO 2015 three-digit survey-group estimate, not an exact EarnWage "
                 "occupation or official MoSPI published table. Descriptive only. "
                 "If the source URL is github.com/Vonter, it is an attributed "
                 "third-party harmonisation of the official PLFS microdata.")
    }


def coverage():
    with connect() as db:
        init(db)
        n, jobs, regions = db.execute("""SELECT COUNT(*), COUNT(DISTINCT nco_code),
            COUNT(DISTINCT CASE WHEN scope='state' THEN state_code END) FROM in_plfs_nco_wages""").fetchone()
        sources = [r[0] for r in db.execute(
            "SELECT DISTINCT source_url FROM in_plfs_nco_wages ORDER BY source_url")]
    from app.in_plfs_derived_import import DERIVATIVE_URL
    secondary = DERIVATIVE_URL in sources
    return {"status": "available" if n else "not_imported",
            "observations": n, "nco_occupations": jobs, "states_or_territories": regions,
            "precision": "broad_nco2015_three_digit_group",
            "occupation_mapping_status": "requires_separate_approved_crosswalk",
            "provenance": "public_third_party_harmonised_microdata" if secondary
                          else "direct_official_microdata" if n else "not_imported",
            "reuse_license": "ODbL 1.0" if secondary else None,
            "source_urls": sources,
            "underlying_official_source_url": MICRODATA_URL}


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--person-csv", required=True)
    cli.add_argument("--manifest", required=True)
    cli.add_argument("--output", default="data/in_plfs_2025_nco.json")
    options = cli.parse_args()
    print(json.dumps(export(options.person_csv, options.manifest, options.output)))

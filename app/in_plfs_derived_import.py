"""Stream an attributed, checksum-pinned public PLFS 2025 *derivative*.

This is not an official direct microdata download. The source is a preprocessed
public dataset traceable to MoSPI's first-visit 2025 release; the resulting
aggregates remain separate NCO-2015 THREE-DIGIT context, not exact EarnWage
occupation salaries. Publish under ODbL with appropriate attribution.
"""
import argparse
import ast
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from app.in_plfs import MICRODATA_URL
from app.in_plfs_microdata import MIN_EFFECTIVE, MIN_SAMPLE, REFERENCE_PERIOD

DERIVATIVE_URL = "https://github.com/Vonter/india-plf-survey"
DERIVATIVE_FILE = "https://github.com/Vonter/india-plf-survey/releases/download/latest/2025.csv.zip"
SOURCE_SHA256 = "a38b88d3d1f84479bfebd9dcd7e9c8771490cf16151bd84aa22128b4796a5ffa"
DERIVATIVE_COMMIT = "1c5cdf139bb82305bf510b91c77c57d0c446436d"
EXPECTED_PERSON_ROWS = 1_148_634
REQUIRED = {
    "Survey Year", "Visit", "State/UT", "CWS Status", "CWS Occupation",
    "CWS Earnings (Salaried)", "Person Final Weight",
    "Quarter", "Sector", "Stratum", "First Stage Unit (FSU)",
}
REGULAR = {
    "worked as regular salaried/wage employee",
    "had regular salaried/wage employment but did not work due to: sickness",
    "had regular salaried/wage employment but did not work due to: other reasons",
}


def read_reviewed_occupation_labels(mapping_py):
    """Read only the literal occupation dictionary with ast; never execute remote code."""
    tree = ast.parse(Path(mapping_py).read_text(encoding="utf-8"))
    candidates = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(isinstance(t, ast.Name) and t.id == "OCCUPATION_CODE" for t in targets):
                candidates.append(ast.literal_eval(stmt.value))
    if len(candidates) != 1:
        raise ValueError("Missing unambiguous pinned NCO occupational dictionary")
    codes = candidates[0]
    by_label = {}
    for code, name in codes.items():
        if not (isinstance(code, int) and 100 <= code <= 999 and isinstance(name, str)):
            raise ValueError("Invalid three-digit NCO mapping")
        if name in by_label:
            raise ValueError("Ambiguous NCO derivative labels")
        by_label[name] = str(code)
    return by_label


def read_reviewed_states(mapping_csv):
    """Reverse-map a pinned State Name/State Code table, reject inconsistencies."""
    states = {}
    with open(mapping_csv, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"State Name", "State Code"}.issubset(reader.fieldnames or []):
            raise ValueError("Missing State code columns")
        for row in reader:
            name = row["State Name"].strip()
            code = row["State Code"].strip().lstrip("0") or "0"
            if not name or not re.fullmatch(r"\d{1,3}", code):
                raise ValueError("Invalid state code")
            previous = states.setdefault(name, code)
            if previous != code:
                raise ValueError("State has contradictory codes")
    if len(states) < 30:
        raise ValueError("Incomplete State/UT mapping")
    return states


def generate(zip_path, mapping_py, mapping_csv, output):
    if hashlib.sha256(Path(zip_path).read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Public derivative checksum mismatch")
    jobs = read_reviewed_occupation_labels(mapping_py)
    states = read_reviewed_states(mapping_csv)
    stats = defaultdict(lambda: [0, 0., 0., 0., set()])
    n_rows = 0
    eligible = 0
    unknown_jobs = set()
    unknown_states = set()
    invalid_pay = 0
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != "2025.csv":
            raise ValueError("Unexpected zipped derivative content")
        if not 1_000_000_000 < members[0].file_size < 2_500_000_000:
            raise ValueError("Unexpected uncompressed derivative size")
        with archive.open(members[0]) as binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            if len(set(header)) != len(header) or not REQUIRED.issubset(header):
                raise ValueError("Derivative schema drift")
            idx = {k: header.index(k) for k in REQUIRED}
            for row in reader:
                n_rows += 1
                if row[idx["Survey Year"]] != "2025" or row[idx["Visit"]] != "V1":
                    raise ValueError("Derivative is not exclusively 2025 first-visit")
                if row[idx["CWS Status"]] not in REGULAR:
                    continue
                eligible += 1
                state_name = row[idx["State/UT"]].strip()
                code = states.get(state_name)
                if not code:
                    unknown_states.add(state_name)
                    continue
                occupation_name = row[idx["CWS Occupation"]].strip()
                soc = jobs.get(occupation_name)
                if not soc:
                    unknown_jobs.add(occupation_name)
                    continue
                try:
                    earnings = float(row[idx["CWS Earnings (Salaried)"]])
                    weight = float(row[idx["Person Final Weight"]])
                except (ValueError, TypeError):
                    invalid_pay += 1
                    continue
                if (not math.isfinite(earnings) or earnings < 0 or earnings > 100_000_000
                        or not math.isfinite(weight) or weight <= 0):
                    invalid_pay += 1
                    continue
                fsu = row[idx["First Stage Unit (FSU)"]].strip()
                if not fsu:
                    raise ValueError("Missing first-stage sampling unit")
                psu = (code, row[idx["Quarter"]], row[idx["Sector"]],
                       row[idx["Stratum"]], fsu)
                for scope in ("national", code):
                    slot = stats[(soc, scope)]
                    slot[0] += 1
                    slot[1] += weight
                    slot[2] += weight ** 2
                    slot[3] += weight * earnings
                    slot[4].add(psu)
    if n_rows != EXPECTED_PERSON_ROWS:
        raise ValueError(f"Derivative person-count mismatch: {n_rows}")
    if unknown_states:
        raise ValueError(f"Unmapped State/UT source labels: {sorted(unknown_states)}")
    if eligible < 100_000:
        raise ValueError("Unexpectedly few salaried respondents")
    published = []
    suppressed = 0
    by_code = {code: name for name, code in jobs.items()}
    state_names = {code: name for name, code in states.items()}
    for (soc, scope), (n, sumw, sumw2, sum_pay, psus) in sorted(stats.items()):
        effective = (sumw ** 2 / sumw2) if sumw2 else 0
        if n < MIN_SAMPLE or effective < MIN_EFFECTIVE or len(psus) < 10:
            suppressed += 1
            continue
        published.append({
            "nco2015_code": soc, "nco2015_label": by_code[soc],
            "geography": "national" if scope == "national" else "state",
            "state_code": None if scope == "national" else scope,
            "state_name": None if scope == "national" else state_names[scope],
            "mean_monthly_earnings": round(sum_pay / sumw, 2),
            "sample_n": n,
            "effective_n_approx": round(effective, 1),
            "observed_psu_count_approx": len(psus),
            "currency": "INR", "unit": "INR/month",
            "population": "CWS regular salaried/wage employees",
            "measure": "survey_weighted_mean_preceding_calendar_month",
            "precision": "broad_nco2015_three_digit_group",
            "period": REFERENCE_PERIOD, "source": "Vonter preprocessed MoSPI PLFS 2025; ODbL 1.0",
            "source_url": DERIVATIVE_URL,
        })
    # Separate dataset, published with both links and ODbL, not represented as
    # direct official ingestion or exact occupation-level salary.
    payload = {
        "schema": 1, "survey": "DDI-IND-NSO-PLFS-Jan2025-Dec2025",
        "period": REFERENCE_PERIOD, "source_kind": "third_party_preprocessed_official_microdata",
        "source_url": DERIVATIVE_URL,
        "underlying_official_source_url": MICRODATA_URL,
        "derivative_release_url": DERIVATIVE_FILE,
        "derivative_sha256": SOURCE_SHA256,
        "derivative_source_commit": DERIVATIVE_COMMIT,
        "reuse_license": "Open Database License (ODbL) v1.0; attribution and share-alike apply",
        "precision": "broad_nco2015_three_digit_group",
        "limitation": ("Weighted descriptive survey means; not occupation offers or exact "
                       "EarnWage jobs; state cells exclude small samples; estimates "
                       "lack design-based variance and are not official MoSPI tables."),
        "records": published,
    }
    if len(published) < 50:
        raise ValueError("Insufficient publishable NCO data")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"source_rows": n_rows, "regular_salaried_rows": eligible,
            "invalid_pay": invalid_pay, "unknown_occupation_labels": sorted(unknown_jobs),
            "published_cells": len(published), "suppressed_cells": suppressed,
            "states": len({r["state_code"] for r in published if r["state_code"]}),
            "nco_groups": len({r["nco2015_code"] for r in published})}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True)
    p.add_argument("--mappings", required=True)
    p.add_argument("--states", required=True)
    p.add_argument("--output", default="data/in_plfs_2025_nco.json")
    a = p.parse_args()
    print(json.dumps(generate(a.zip, a.mappings, a.states, a.output), ensure_ascii=False))

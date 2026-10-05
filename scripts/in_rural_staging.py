"""Audit the complete Labour Bureau rural CSV; private staging only.

Website policy and terms currently conflict on reproduction permission.
No production importer consumes this output. Survey-year labels are preserved;
daily rural rates are never converted to monthly salaries or general-market pay.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

URL = "https://www.labourbureau.gov.in/home/excel_download_ruralWage_data?state_id=1"
FIELDS = ["S.No", "Year", "Month", "State", "Occupation", "Item", "Men", "Women"]
KEYS = ("Year", "Month", "State", "Occupation", "Item")
MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}


def audit(body):
    if not isinstance(body, bytes) or not 0 < len(body) <= 32_000_000:
        raise ValueError("Invalid rural CSV size")
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if reader.fieldnames != FIELDS:
        raise ValueError("Unexpected rural CSV columns")
    grouped = defaultdict(list)
    counts = Counter()
    original_rows = 0
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed rural row")
        if (not re.fullmatch(r"[0-9]{4}-[0-9]{4}", row["Year"])
                or row["Month"] not in MONTHS or not row["State"].strip()
                or not row["Item"].strip() or row["Occupation"].strip() not in ("Agriculture", "Non-Agriculture")):
            raise ValueError("Unreviewed rural dimensions")
        original_rows += 1
        key = tuple(row[k].strip() for k in KEYS)
        grouped[key].append((row["Men"], row["Women"]))
        for value in (row["Men"], row["Women"]):
            if value in ("-", "@", ""):
                counts[{"-": "operation_unavailable", "@": "fewer_than_five_quotes", "": "missing"}[value]] += 1
            else:
                try:
                    n = Decimal(value)
                except InvalidOperation as exc:
                    raise ValueError("Unknown rural value or flag") from exc
                if not n.is_finite() or n <= 0:
                    raise ValueError("Invalid rural daily rate")
                counts["positive_numeric"] += 1
    conflicts = [dict(zip(KEYS, key)) for key, values in grouped.items() if len(set(values)) > 1]
    metadata = {
        "schema_version": 1, "country": "IN", "publication_status": "private_staging_only",
        "source_url": URL, "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_bytes": len(body), "source_rows": original_rows,
        "source_cells": original_rows * 2, "unique_row_identities": len(grouped),
        "duplicate_rows": original_rows - len(grouped), "conflicting_identities": len(conflicts),
        "source_cell_status_counts": dict(counts),
        "survey_years": sorted({key[0] for key in grouped}),
        "geographies": sorted({key[2] for key in grouped}),
        "original_occupation_labels": sorted({key[4] for key in grouped}),
        "unit": "INR per standardised 8-hour working day",
        "scope": "rural wage-rate quotations; state and All India aggregates; sex-specific",
        "methodology_url": "https://www.labourbureau.gov.in/uploads/pdf/Wage_Rates_Rural_India_A_Brief.pdf",
        "series_break": "Sample expanded from 600 villages/20 States-UTs to 787 villages/34 States-UTs from July 2025. Comparisons require care.",
        "reuse_blockers": ["websitepolicy requires prior reproduction permission; termsandconditions permits free reproduction with attribution",
                          str(len(conflicts)) + " conflicting identities in acquired export require source review"],
        "reuse_urls": ["https://www.labourbureau.gov.in/websitepolicy", "https://www.labourbureau.gov.in/termsandconditions"],
        "conflict_keys": conflicts,
    }
    staging = metadata | {"rows": [dict(zip(KEYS, key)) | {
        "original_values": values,
        "quality_status": "conflicting_duplicates" if len(set(values)) > 1 else "source_values_preserved",
    } for key, values in grouped.items()]}
    return metadata, staging


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    runtime = Path(__file__).resolve().parents[1] / "data"
    if args.output.resolve().is_relative_to(runtime.resolve()):
        raise ValueError("Private staging must remain outside runtime data")
    metadata, staging = audit(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(staging, ensure_ascii=False, separators=(",", ":")) + "\n")
    args.audit.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: metadata[k] for k in ("source_rows", "source_cells", "conflicting_identities")}))

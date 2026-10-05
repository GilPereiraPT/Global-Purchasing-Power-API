"""Reproduce reviewed PT/PK group snapshots from downloaded official originals.

New dimensions, years or labels require a separate source review.
PK PDF extraction requires Poppler's pdftotext; respondent data are never used.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.official_group_earnings import FILES, ROOT, load


def extract_pt(body, reviewed):
    payload = json.loads(body)
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("Unexpected INE payload")
    obj = payload[0]
    if (obj.get("IndicadorCod") != "0012655"
            or obj.get("IndicadorDsg") != "Ganho médio mensal (€) por Localização geográfica (NUTS - 2024) e Profissão (CPP); Anual - MTSSS/GEP, Quadros de pessoal"
            or set(obj.get("Dados", {})) != set(reviewed["periods"])):
        raise ValueError("Unreviewed Portuguese indicator, concept or period")
    rows = []
    for period, items in obj["Dados"].items():
        if len(items) != len(reviewed["groups"]):
            raise ValueError("Incomplete Portuguese groups")
        for item in items:
            group = item.get("dim_3")
            if (item.get("geocod") != "PT" or item.get("geodsg") != "Portugal"
                    or group not in reviewed["groups"]
                    or item.get("dim_3_t") != reviewed["groups"][group]):
                raise ValueError("Unreviewed geography or group label")
            value = item.get("valor")
            if value is not None and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", str(value)):
                raise ValueError("Unreviewed value/suppression encoding")
            rows.append({"period": period, "group": group, "sex": "both", "measure": "mean",
                         "geography": "national", "value": float(value) if value is not None else None,
                         "status": "available" if value is not None else "unavailable"})
    return rows


def extract_pk(text, reviewed):
    heading = "Table 5.4 Average Monthly Wages by Major Occupational Groups and Sex\n"
    if text.count(heading) != 1:
        raise ValueError("Missing or ambiguous PBS table")
    text = text.split(heading)[1].split("As shown in Table-5.4")[0]
    if not all(period in text for period in reviewed["periods"]):
        raise ValueError("Unreviewed periods")
    rows = []
    for group, label in reviewed["groups"].items():
        pattern = "^" + re.escape(label) + r"\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$"
        matches = re.findall(pattern, text, re.M)
        if len(matches) != 2:
            raise ValueError("Changed PBS table structure or suppressed value: " + group)
        for period, values in zip(reviewed["periods"], matches):
            for index, value in enumerate(values):
                rows.append({"period": period, "group": group,
                             "sex": ("both", "men", "women")[index % 3],
                             "measure": "mean" if index < 3 else "median",
                             "geography": "national", "value": int(value.replace(",", "")),
                             "status": "available"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", choices=("PT", "PK"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reviewed = load(args.country)
    body = args.source.read_bytes()
    if args.country == "PT":
        rows = extract_pt(body, reviewed)
    else:
        text = subprocess.run(["pdftotext", "-layout", str(args.source), "-"],
                              check=True, capture_output=True).stdout.decode()
        rows = extract_pk(text, reviewed)
    reviewed["observations"] = rows
    reviewed["provenance"]["raw_sha256"] = hashlib.sha256(body).hexdigest()
    reviewed["provenance"]["acquired_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reviewed, ensure_ascii=False, indent=2) + "\n")
    load(args.country, args.output)
    print(json.dumps({"country": args.country, "observations": len(rows),
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()

"""Independent PT/Pakistan published group context, never exact job wages."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data"
FILES = {"PT": "pt_ine_group_earnings.json", "PK": "pk_pbs_group_earnings.json"}
SOURCES = {"PT": "INE/GEP Quadros de Pessoal", "PK": "Pakistan Bureau of Statistics, Labour Force Survey"}
SOURCE_URLS = {
    "PT": "https://www.ine.pt/xurl/indx/0012655/PT",
    "PK": "https://www.pbs.gov.pk/wp-content/uploads/2020/07/LFS-2024-25-Annual-Report.pdf",
}


def load(country, path=None):
    if country not in FILES:
        raise ValueError("Unsupported group dataset")
    path = Path(path) if path else ROOT / FILES[country]
    if path.stat().st_size > 1_000_000:
        raise ValueError("Oversized group snapshot")
    data = json.loads(path.read_text())
    if (data.get("schema_version") != 1 or data.get("country") != country
            or data.get("precision") != "published_major_occupation_group"
            or data.get("source") != SOURCES[country]
            or data.get("source_url") != SOURCE_URLS[country]
            or data.get("currency") != {"PT": "EUR", "PK": "PKR"}[country]
            or data.get("publication_status") != "public_with_attribution"
            or not isinstance(data.get("observations"), list) or not data["observations"]):
        raise ValueError("Unrecognised group snapshot")
    seen = set()
    for row in data["observations"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid group row")
        key = tuple(row.get(k) for k in ("period", "group", "sex", "measure", "geography"))
        if (None in key or key in seen or row.get("group") not in data["groups"]
                or row.get("sex") not in ("both", "men", "women")
                or row.get("measure") not in ("mean", "median")
                or row.get("geography") != "national"
                or row.get("period") not in data["periods"]):
            raise ValueError("Duplicate or invalid group identity")
        if country == "PT" and (row["sex"] != "both" or row["measure"] != "mean"):
            raise ValueError("Unpublished Portuguese breakdown")
        seen.add(key)
        value = row.get("value")
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                                  or not 0 < value < 1_000_000):
            raise ValueError("Invalid group wage")
        if row.get("status") not in ("available", "unavailable"):
            raise ValueError("Invalid group status")
        if (value is None) != (row["status"] == "unavailable"):
            raise ValueError("Inconsistent group availability")
    return data


def catalogue(country, path=None):
    try:
        data = load(country, path)
    except FileNotFoundError:
        return {"country": country, "status": "not_imported", "observations": 0,
                "precision": "published_major_occupation_group", "groups": {}, "periods": [],
                "source": SOURCES[country], "source_url": SOURCE_URLS[country]}
    return {k: v for k, v in data.items() if k != "observations"} | {
        "observations": len(data["observations"]),
        "note": "Published major occupational group context; not an individual occupation wage.",
    }


def history(country, group, sex="both", period=None, path=None):
    try:
        data = load(country, path)
    except FileNotFoundError:
        return catalogue(country, path) | {"group": group, "sex": sex, "status": "unavailable",
                                          "observations": [], "reason": "Official group snapshot not imported"}
    if group not in data["groups"] or sex not in ("both", "men", "women"):
        raise ValueError("Unknown group or sex")
    if period is not None and period not in data["periods"]:
        raise ValueError("Unknown reference period")
    rows = [r for r in data["observations"] if r["group"] == group and r["sex"] == sex
            and (period is None or r["period"] == period)]
    return catalogue(country, path) | {"group": group, "group_label": data["groups"][group],
                                      "precision": "all_occupations" if group in ("T", "total") else data["precision"],
                                      "sex": sex, "status": "available" if any(r["value"] is not None for r in rows) else "unavailable",
                                      "observations": rows}

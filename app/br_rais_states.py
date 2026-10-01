"""Verified RAIS 2025 CBO occupation × Brazilian UF snapshot.

Do not extrapolate national medians or combine median values from multiple
occupations. The national composite 'manager' and 'secondary_teacher' are
intentionally excluded from this state-specific snapshot.
"""
import json
from pathlib import Path
from app.br_rais_states_import import UF, MIN_LINKS
from app import br_cbo
from app import br_rais_wages

DATA = {}
SOURCE_FILE = Path(__file__).resolve().parent.parent / "data/br_rais_2025_states.json"


def load(path=SOURCE_FILE):
    global DATA
    file = Path(path)
    if not file.exists():
        DATA = {}
        return 0
    data = json.loads(file.read_text(encoding="utf-8"))
    if (data.get("schema") != 1 or data.get("country") != "BR"
            or data.get("reference_period") != "2025-12"
            or data.get("precision") != "occupation_cbo2002_6_digit"):
        raise ValueError("Unreviewed Brazil state salary snapshot")
    checked = {}
    for row in data["records"]:
        job, state = row["occupation"], row["uf"]
        expected = br_cbo.CBO.get(job)
        if (not expected or job not in br_rais_wages.OBSERVATIONS or state not in UF
                or row["uf_name"] != UF[state]
                or row["cbo_code"] != expected["code"]
                or row["precision"] != "occupation_cbo2002_6_digit"
                or row["currency"] != "BRL" or row["unit"] != "BRL/month"
                or row["measure"] != "median_december_remuneration"
                or row["reference_period"] != "2025-12"
                or row["links"] < MIN_LINKS
                or not isinstance(row["value"], int) or row["value"] <= 0):
            raise ValueError("Unverified or unsafe Brazil occupation/state salary cell")
        key = (job, state)
        if key in checked:
            raise ValueError("Duplicate CBO/state wage")
        checked[key] = row
    DATA = checked
    return len(DATA)


def wage(occupation, uf=None):
    if uf is None:
        return {"status": "not_requested"}
    if uf not in UF:
        raise ValueError("Unknown Brazil UF")
    row = DATA.get((occupation, uf))
    if row is None:
        return {
            "status": "unavailable", "occupation": occupation, "uf": uf,
            "uf_name": UF[uf], "reason": "No verified 2025 RAIS-derived CBO/state median published; national median not substituted",
        }
    return {
        "status": "available", "country": "BR", "occupation": occupation,
        "uf": uf, "uf_name": UF[uf],
        "value": row["value"], "currency": "BRL",
        "unit": "BRL/month", "measure": row["measure"],
        "reference_period": row["reference_period"],
        "cbo_code": row["cbo_code"], "precision": row["precision"],
        "links": row["links"], "source": row["source"],
        "source_url": row["source_url"],
        "official_underlying_source": row["official_underlying_source"],
        "note": "Median December 2025 remuneration for formal employment links with contracted 40–44 hours/week; not net pay.",
    }


def coverage():
    by_state = []
    for code, name in UF.items():
        jobs = [job for job, uf in DATA if uf == code]
        by_state.append({"code": code, "name": name, "occupations": len(jobs),
                         "total_occupations": 40, "observed_cells": len(jobs)})
    return {
        "country": "BR", "status": "available" if DATA else "not_imported",
        "observed_occupations": len({job for job, _ in DATA}),
        "states_with_data": len({uf for _, uf in DATA}),
        "total_states": 27, "observed_cells": len(DATA),
        "precision": "occupation_cbo2002_6_digit",
        "source_kind": "RAIS-derived third-party published CBO×UF tables",
        "by_state": by_state,
    }

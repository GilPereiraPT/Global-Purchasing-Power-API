"""German Bundesland occupational medians, strict Entgeltatlas Berufsgattung scope.

State observation import requires a reviewed BA extract; no silent fallback to
Berufsgruppe, other regions, capped medians (>8050), or guessed year.
Official help: https://www.arbeitsagentur.de/hilfe-entgeltatlas
"""
import json
import math
from pathlib import Path
from app.de_entgeltatlas_wages import APPROVED, YEAR, AGGREGATION_LEVEL, PRECISION, DEFAULT as NATIONAL_SNAPSHOT

STATES = {
    "BW": ("Baden-Württemberg", 11), "BY": ("Bayern", 12),
    "BE": ("Berlin", 14), "BB": ("Brandenburg", 15),
    "HB": ("Bremen", 7), "HH": ("Hamburg", 5),
    "HE": ("Hessen", 9), "MV": ("Mecklenburg-Vorpommern", 16),
    "NI": ("Niedersachsen", 6), "NW": ("Nordrhein-Westfalen", 8),
    "RP": ("Rheinland-Pfalz", 10), "SL": ("Saarland", 13),
    "SN": ("Sachsen", 17), "ST": ("Sachsen-Anhalt", 18),
    "SH": ("Schleswig-Holstein", 4), "TH": ("Thüringen", 19),
}
DEFAULT = Path(__file__).resolve().parent.parent / "data/de_entgeltatlas_states_2025.json"
REQUIRED = {
    "occupation", "state", "value", "reference_period", "currency", "unit",
    "measure", "precision", "aggregation_level", "evidence_page_id",
    "source_url", "state_ba_region_id", "profession_title",
    "occupational_aggregate", "requirement_level", "raw_ba_evidence_reference",
}
DATA = {}


def validate(obj):
    if (not isinstance(obj, dict) or obj.get("schema") != 1
            or obj.get("country") != "DE" or obj.get("reference_period") != YEAR
            or not isinstance(obj.get("records"), list)):
        raise ValueError("Unreviewed Entgeltatlas regional metadata")
    # Check the selected German profession and classification against the
    # already approved, committed national occupation/classification record.
    national = json.loads(NATIONAL_SNAPSHOT.read_text(encoding="utf-8"))
    national_index = {r["occupation"]: r for r in national["records"]}
    observed = {}
    for row in obj["records"]:
        if not isinstance(row, dict) or set(row) != REQUIRED:
            raise ValueError("Invalid Entgeltatlas regional record schema")
        occupation, state = row["occupation"], row["state"]
        approved = APPROVED.get(occupation)
        national_row = national_index.get(occupation)
        state_info = STATES.get(state)
        value = row["value"]
        if (approved is None or national_row is None or state_info is None or
                row["profession_title"] != national_row["profession_title"] or
                row["occupational_aggregate"] != national_row["occupational_aggregate"] or
                row["requirement_level"] != national_row["requirement_level"] or
                row["evidence_page_id"] != approved[0] or
                row["state_ba_region_id"] != state_info[1] or
                row["source_url"] != "https://web.arbeitsagentur.de/entgeltatlas/beruf/" + approved[0] or
                row["reference_period"] != YEAR or row["currency"] != "EUR"
                or row["unit"] != "EUR/month" or row["measure"] != "median"
                or row["precision"] != PRECISION
                or row["aggregation_level"] != AGGREGATION_LEVEL
                or row["requirement_level"] not in ("Helfer", "Fachkraft", "Spezialist", "Experte")
                or not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value) or value <= 0 or value > 8050
                or not row["profession_title"] or not row["occupational_aggregate"]
                or not isinstance(row["raw_ba_evidence_reference"], str)
                or not row["raw_ba_evidence_reference"].strip()):
            raise ValueError("Regional wage unverified, capped, reclassified or otherwise invalid")
        key = (occupation, state)
        if key in observed:
            raise ValueError("Duplicate state and profession")
        observed[key] = row
    return observed


def load(path=DEFAULT):
    global DATA
    filename = Path(path)
    if not filename.is_file():
        DATA = {}
        return 0
    obj = json.loads(filename.read_text(encoding="utf-8"))
    DATA = validate(obj)
    return len(DATA)


def wage(occupation, state=None):
    if not state:
        return {"status": "not_requested", "country": "DE"}
    if state not in STATES:
        raise ValueError("Unknown German federal state")
    row = DATA.get((occupation, state))
    if row is None:
        return {
            "status": "unavailable", "country": "DE", "occupation": occupation,
            "state": state, "state_name": STATES[state][0],
            "reason": ("No verified state-level BA Berufsgattung median imported. "
                       "National median, wider Berufsgruppe or other region not substituted."),
        }
    return {
        "status": "available", "country": "DE", "occupation": occupation,
        "state": state, "state_name": STATES[state][0],
        "value": row["value"], "currency": "EUR", "unit": "EUR/month",
        "measure": "median", "reference_period": YEAR,
        "precision": PRECISION, "aggregation_level": AGGREGATION_LEVEL,
        "source": "Bundesagentur für Arbeit — Entgeltatlas",
        "source_url": row["source_url"],
        "evidence_page_id": row["evidence_page_id"],
        "profession_title": row["profession_title"],
        "occupational_aggregate": row["occupational_aggregate"],
        "raw_ba_evidence_reference": row["raw_ba_evidence_reference"],
        "note": "Regional median monthly gross full-time social-security pay, not net; direct Berufsgattung only.",
    }


def coverage():
    by_state = [
        {"code": state, "name": STATES[state][0],
         "observed_occupations": len({job for job, region in DATA if region == state}),
         "possible_occupations": 40}
        for state in STATES
    ]
    return {
        "country": "DE", "status": "available" if DATA else "pending_verified_regional_import",
        "total_states": len(STATES),
        "states_with_data": sum(row["observed_occupations"] > 0 for row in by_state),
        "observed_occupations": len({job for job, _ in DATA}),
        "observed_cells": len(DATA),
        "precision": PRECISION,
        "by_state": by_state,
        "warning": ("Only exact Berufsgattung state data count. "
                    "The BA service may suggest broader Berufsgruppe/regions below its disclosure threshold."),
    }

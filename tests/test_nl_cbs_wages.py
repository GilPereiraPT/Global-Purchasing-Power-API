"""CBS Netherlands committed wage snapshot invariants; no live network."""
import json
from pathlib import Path

from app import nl_cbs_wages as nl
from app import store


def snapshot_path():
    return Path(__file__).resolve().parent.parent / "data" / "nl_cbs_wages.json"


def test_committed_snapshot_contains_only_approved_brc_mappings():
    obj = json.loads(snapshot_path().read_text(encoding="utf-8"))
    rows = nl.validate_snapshot(obj)
    assert len(rows) == len(nl.APPROVED) == 21
    assert all(row["country"] == "NL" for row in obj["records"])
    assert all(row["measure"] == "median" and row["unit"] == "EUR/hour"
               for row in obj["records"])
    assert all(row["salary_concept"] ==
               "gross_hourly_median_excluding_special_pay_and_overtime"
               for row in obj["records"])


def test_ambiguous_or_unpublished_professions_are_not_admitted():
    for occupation in (
        "auditor", "doctor", "nurse", "pharmacist", "teacher",
        "civil_engineer", "mechanical_engineer", "manager",
        "supermarket_worker", "bus_driver", "plumber", "construction_worker",
        "lawyer", "dentist", "data_analyst", "welder", "agricultural_worker",
    ):
        assert occupation not in nl.APPROVED


def test_latest_published_period_is_preserved_per_occupation(tmp_path, monkeypatch):
    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(nl, "connect", store.connect)
    assert nl.load_snapshot(snapshot_path()) == 21

    software = nl.wages("NL", "software_developer")
    assert software["status"] == "available"
    assert software["value"] == 34.5
    assert software["reference_period"] == "2025"
    assert software["publication_status"] == "provisional"
    assert software["source_unit"] == "EUR/hour"

    teacher = nl.wages("NL", "secondary_teacher")
    assert teacher["value"] == 35.4
    assert teacher["reference_period"] == "2024"
    assert teacher["publication_status"] == "definitive"


def test_hourly_cbs_value_is_never_annualized(tmp_path, monkeypatch):
    from app import earnwage_history as history

    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(nl, "connect", store.connect)
    monkeypatch.setattr(history, "connect", store.connect)
    assert nl.load_snapshot(snapshot_path()) == 21
    result = history.exact_history("NL", "software_developer", 2025, 2025)
    item = result["observations"][0]
    assert item["status"] == "available"
    assert item["annual_presentation"]["status"] == "unavailable"
    assert item["reported_hourly"]["unit"] == "per_hour"
    assert item["reported_hourly"]["kind"] == "reported_hourly"
    assert item["reported_hourly"]["value"] == 34.5

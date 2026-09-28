"""Germany Entgeltatlas snapshot invariants; no live network in tests."""
import json
from pathlib import Path

from app import de_entgeltatlas_wages as de
from app import store


def snapshot():
    path = Path(__file__).resolve().parent.parent / "data" / "de_entgeltatlas_wages.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_snapshot_has_only_approved_direct_berufsgattung_rows():
    obj = snapshot()
    rows = de.validate_snapshot(obj)
    assert len(rows) == 27
    assert len(obj["records"]) == len(de.APPROVED) == 27
    assert all(row["aggregation_level"] == "Berufsgattung" for row in obj["records"])
    assert all(row["precision"] == de.PRECISION for row in obj["records"])
    assert all(row["measure"] == "median" and row["unit"] == "EUR/month"
               for row in obj["records"])


def test_ambiguous_or_fallback_prone_titles_are_not_admitted():
    for job in ("auditor", "pharmacist", "psychologist", "teacher", "it_technician",
                "manager", "receptionist", "supermarket_worker",
                "construction_worker", "data_analyst", "warehouse_operator",
                "industrial_operator", "agricultural_worker"):
        assert job not in de.APPROVED


def test_load_and_read_preserves_monthly_median(tmp_path, monkeypatch):
    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(de, "connect", store.connect)
    path = Path(__file__).resolve().parent.parent / "data" / "de_entgeltatlas_wages.json"
    assert de.load_snapshot(path) == 27
    wage = de.wages("DE", "software_developer")
    assert wage["status"] == "available"
    assert wage["value"] == 6301
    assert wage["currency"] == "EUR"
    assert wage["measure"] == "median"
    assert wage["source_unit"] == "EUR/month"
    assert wage["aggregation_level"] == "Berufsgattung"
    assert wage["precision"] == de.PRECISION


def test_unapproved_title_never_uses_broader_fallback(tmp_path, monkeypatch):
    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(de, "connect", store.connect)
    result = de.wages("DE", "pharmacist")
    assert result["status"] == "unavailable"
    assert "fallback" in result["reason"]

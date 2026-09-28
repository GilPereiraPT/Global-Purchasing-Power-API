"""France INSEE committed snapshot invariants; no live network in tests."""
import json
from pathlib import Path

from app import fr_insee_wages as fr
from app import store


def snapshot_path():
    return Path(__file__).resolve().parent.parent / "data" / "fr_insee_wages.json"


def test_committed_snapshot_has_only_approved_detailed_pcs_ese_rows():
    obj = json.loads(snapshot_path().read_text(encoding="utf-8"))
    rows = fr.validate_snapshot(obj)
    assert len(rows) == len(fr.APPROVED) == 23
    assert all(row["country"] == "FR" for row in obj["records"])
    assert all(row["measure"] == "mean" and row["unit"] == "EUR/month"
               for row in obj["records"])
    assert all(row["salary_concept"] == "net_monthly_mean_full_time_equivalent"
               for row in obj["records"])
    assert all(row["employment_scope"] == "private_sector_employees"
               for row in obj["records"])


def test_ambiguous_split_or_public_dominant_titles_are_not_admitted():
    for job in (
        "accountant", "auditor", "financial_analyst", "teacher",
        "software_developer", "administrative_assistant", "manager",
        "receptionist", "sales_assistant", "construction_worker", "waiter",
        "data_analyst", "cybersecurity_specialist", "secondary_teacher",
        "warehouse_operator", "industrial_operator", "agricultural_worker",
    ):
        assert job not in fr.APPROVED


def test_load_and_read_preserves_net_monthly_mean_scope(tmp_path, monkeypatch):
    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(fr, "connect", store.connect)
    assert fr.load_snapshot(snapshot_path()) == 23
    wage = fr.wages("FR", "nurse")
    assert wage["status"] == "available"
    assert wage["value"] == 2715.20
    assert wage["currency"] == "EUR"
    assert wage["measure"] == "mean"
    assert wage["source_unit"] == "EUR/month"
    assert wage["salary_concept"] == "net_monthly_mean_full_time_equivalent"
    assert wage["employment_scope"] == "private_sector_employees"
    assert wage["classification"] == "PCS-ESE 2003:431F"


def test_unapproved_title_does_not_select_one_of_several_pcs_categories(
        tmp_path, monkeypatch):
    db = tmp_path / "wages.sqlite"
    monkeypatch.setattr(store, "DB_PATH", str(db))
    monkeypatch.setattr(fr, "connect", store.connect)
    result = fr.wages("FR", "software_developer")
    assert result["status"] == "unavailable"
    assert "ambiguous" in result["reason"]

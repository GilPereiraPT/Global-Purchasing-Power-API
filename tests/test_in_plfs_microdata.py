"""Contract and disclosure tests for the official PLFS 2025 microdata pipeline."""
import csv
import json

import pytest
from fastapi.testclient import TestClient

from app import store
from app.in_plfs_microdata import aggregate, export, load_snapshot, wages, coverage
from app.main import app

FIELDS = ["visit", "st", "sec", "acws", "ocu_cws", "ern_reg",
          "mult", "mfsu", "qtr", "month"]
MANIFEST = {
    "survey": "DDI-IND-NSO-PLFS-Jan2025-Dec2025",
    "verified_person_file": "cperv12025",
    "official_state_crosswalk_reviewed": True,
    "states": {"27": "Synthetic Maharashtra", "7": "Synthetic Delhi"},
    "occupations": {"251": "Synthetic verified NCO code", "222": "Second verified NCO"},
    "first_visit_code": "1",
    "regular_employee_cws_codes": ["31", "71", "72"],
    "multiplier_scale": 100,
}


def person_file(path):
    rows = []
    for i in range(65):
        rows.append(["1", "27", "2", "31", "251", "10000" if i < 32 else "20000",
                     "100", str(i % 13 + 1), "1", "1"])
    # A second occupation's state-specific results must remain suppressed.
    for i in range(15):
        rows.append(["1", "7", "2", "31", "222", "999999",
                     "100", str(i + 1), "1", "1"])
    # Never include casual, self-employed or revisit respondents.
    rows.extend([
        ["1", "27", "2", "51", "251", "999999", "100", "2", "1", "1"],
        ["2", "27", "2", "31", "251", "999999", "100", "2", "1", "1"],
        ["1", "27", "2", "31", "251", "", "100", "2", "1", "1"],
    ])
    with open(path, "w", encoding="utf8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)


def test_disclosure_filter_weighted_mean_and_snapshot_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "persons.csv"
    person_file(path)
    cells, info = aggregate(path, MANIFEST)
    assert info["eligible_regular_employees"] == 81
    assert info["missing_earnings"] == 1
    assert info["suppressed_cells"] == 2
    assert len(cells) == 2  # same NCO at state and national scopes only
    state = next(x for x in cells if x["geography"] == "state")
    assert state["sample_n"] == 65
    assert state["mean_monthly_earnings"] == round((32 * 10000 + 33 * 20000) / 65, 2)
    assert state["state_code"] == "27"
    manifest = tmp_path / "reviewed.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf8")
    snapshot = tmp_path / "result.json"
    result = export(path, manifest, snapshot)
    assert result["published_cells"] == 2
    assert "Synthetic" not in snapshot.read_text(encoding="utf8").split("records")[0]
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "isolated.sqlite"))
    assert load_snapshot(snapshot) == 2
    assert wages("251", "27")["status"] == "available"
    assert wages("251", "7")["status"] == "unavailable"
    assert wages("251")["status"] == "available"
    assert coverage()["observations"] == 2


def test_fails_closed_on_unreviewed_crosswalk_and_wrong_schema(tmp_path):
    path = tmp_path / "persons.csv"
    person_file(path)
    with pytest.raises(ValueError, match="crosswalk"):
        aggregate(path, {**MANIFEST, "official_state_crosswalk_reviewed": False})
    with pytest.raises(ValueError, match="regular"):
        aggregate(path, {**MANIFEST, "regular_employee_cws_codes": ["31"]})
    path.write_text("wrong,fields\n1,2\n", encoding="utf8")
    with pytest.raises(ValueError, match="columns"):
        aggregate(path, MANIFEST)


def test_nco_api_is_explicitly_unavailable_without_import(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "empty.sqlite"))
    with TestClient(app) as client:
        c = client.get("/v1/in/plfs/nco/coverage").json()
        assert c["status"] == "not_imported"
        assert c["occupation_mapping_status"] == "requires_separate_approved_crosswalk"
        x = client.get("/v1/in/plfs/nco/251?state=27").json()
        assert x["status"] == "unavailable"
        assert client.get("/v1/in/plfs/nco/nope").status_code == 422

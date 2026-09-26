import json

import pytest

import app.store as store
from app.ilostat_import import export_snapshot, import_csv, load_snapshot, salary


def test_salary_snapshot_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "source.sqlite3"))
    with store.connect() as db:
        import_csv(db, """ref_area,source,indicator,sex,classif1,classif2,time,obs_value
BRA,TEST_SOURCE,EAR_SAMPLE,SEX_T,OCU_ISCO08_2411,CUR_TYPE_LCU,2025,5400
""", "EAR_SAMPLE_A", "Average monthly earnings of employees by sex, occupation and currency")
    snapshot = tmp_path / "salaries.json"
    assert export_snapshot(snapshot)["observations"] == 1
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["observations"][0]["value"] == 5400
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "restored.sqlite3"))
    assert load_snapshot(snapshot) == 1
    assert salary("BR", "accountant")["value"] == 5400


def test_reject_bad_snapshot_and_empty_export(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "empty.sqlite3"))
    with pytest.raises(ValueError, match="No ILOSTAT"):
        export_snapshot(tmp_path / "empty.json")
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": 1, "source":"ILOSTAT", "observations":[{"country":"XX","occupation":"accountant"}]}')
    with pytest.raises(ValueError, match="Unknown country"):
        load_snapshot(bad)

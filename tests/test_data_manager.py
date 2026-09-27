"""Offline integration tests for authenticated browser-driven data consolidation."""
import io
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from app import data_manager as dm, native_wsgi, store
from app.country_insights_store import connect as econ_connect, read_indicator, save_result


def request(action, data=None, token=None, origin=None, method="POST"):
    status, headers = [], []
    payload = json.dumps(data if data is not None else {}).encode("utf-8")
    env = {
        "PATH_INFO": "/v1/admin/data-manager/" + action,
        "REQUEST_METHOD": method,
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(payload),
        "CONTENT_LENGTH": str(len(payload)),
    }
    if token:
        env["HTTP_X_EARNWAGE_ADMIN_TOKEN"] = token
    if origin is not None:
        env["HTTP_ORIGIN"] = origin
    def start(response_status, response_headers):
        status.append(response_status)
        headers.extend(response_headers)
    raw = b"".join(native_wsgi.application(env, start))
    return int(status[0].split()[0]), json.loads(raw) if raw else None, dict(headers)


def setup(monkeypatch, tmp_path):
    secret = "s" * 40
    monkeypatch.setenv("EARNWAGE_ADMIN_TOKEN", secret)
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB",
                       str(tmp_path / "real_insights.sqlite3"))
    monkeypatch.setenv("GPP_CACHE_DB",
                       str(tmp_path / "real_wages.sqlite3"))
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "real_wages.sqlite3"))
    monkeypatch.setattr(dm, "BACKUP_DIR", tmp_path / "private_backup_dir")
    with econ_connect() as db:
        save_result(db, "PT", "life_expectancy",
                    [{"year": 2024, "value": 82.1}], "available")
    with store.connect():
        pass
    return secret


def test_admin_only_no_get_or_public_import(monkeypatch, tmp_path):
    secret = setup(monkeypatch, tmp_path)
    assert request("status")[0] == 401
    assert request("status", token="bad")[0] == 401
    assert request("status", token=secret, origin="https://other.example")[0] == 403
    assert request("status", token=secret, method="GET")[0] == 405
    code, _, headers = request("status", origin=dm.ALLOW_ORIGIN, method="OPTIONS")
    assert code == 204
    assert headers["Access-Control-Allow-Origin"] == dm.ALLOW_ORIGIN
    code, data, headers = request("status", token=secret, origin=dm.ALLOW_ORIGIN)
    assert code == 200 and data["status"] == "ok"
    assert headers["Access-Control-Allow-Origin"] == dm.ALLOW_ORIGIN
    monkeypatch.delenv("EARNWAGE_ADMIN_TOKEN")
    assert request("status", token=secret)[0] == 503


def test_preview_never_imports_and_backup_is_required(monkeypatch, tmp_path):
    secret = setup(monkeypatch, tmp_path)
    payload = {"source": "world_bank", "country": "PT",
               "indicator": "inflation_annual", "mode": "missing"}
    with patch.object(dm, "_fetch", side_effect=AssertionError("network called")):
        code, data, _ = request("import", {**payload, "dry_run": True},
                                token=secret)
        assert code == 200 and data["import_status"] == "would_import"
        code, data, _ = request("import", payload, token=secret)
        assert code == 409 and data["import_status"] == "backup_required"
        code, data, _ = request("import", {
            **payload, "indicator": "life_expectancy"}, token=secret)
        assert code == 200 and data["import_status"] == "skipped_existing"
    code, data, _ = request("import", {**payload, "indicator": "invented"},
                            token=secret)
    assert code == 422 and data["error"] == "invalid_manager_request"


def test_real_private_backup_import_and_audit(monkeypatch, tmp_path):
    secret = setup(monkeypatch, tmp_path)
    from scripts import backup_earnwage_data as backup
    monkeypatch.setattr(backup, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    code, data, _ = request("backup", {}, token=secret)
    assert code == 200 and data["status"] == "available"
    assert data["databases"]["insights"]["integrity"] == "ok"
    assert data["databases"]["wages_cache"]["integrity"] == "ok"
    private = dm.BACKUP_DIR / data["backup_id"]
    assert (private / "manifest.json").is_file()
    assert (private / "insights.sqlite3").is_file()
    payload = {"source": "world_bank", "country": "PT",
               "indicator": "inflation_annual", "mode": "missing"}
    with patch.object(dm, "_fetch", return_value=(
            "available", [{"year": 2025, "value": 2.4}], None)):
        code, data, _ = request("import", payload, token=secret)
    assert code == 200 and data["import_status"] == "available"
    assert data["data"]["year"] == 2025
    with econ_connect() as db:
        assert read_indicator(db, "PT", "inflation_annual")["value"] == 2.4
    status, data, _ = request("status", {}, token=secret)
    assert status == 200 and data["history"][0]["indicator"] == "inflation_annual"
    assert data["backups"][0] == private.name
    assert str(tmp_path) not in json.dumps(data)


def test_forced_retry_retains_prior_observation(monkeypatch, tmp_path):
    secret = setup(monkeypatch, tmp_path)
    (dm.BACKUP_DIR / "backup-test").mkdir(parents=True)
    (dm.BACKUP_DIR / "backup-test" / "manifest.json").write_text("{}")
    with patch.object(dm, "_fetch", return_value=(
            "upstream_unavailable", [], "TimeoutError")):
        code, data, _ = request("import", {
            "source": "world_bank", "country": "PT",
            "indicator": "life_expectancy", "mode": "refresh"}, token=secret)
    assert code == 200 and data["import_status"] == "failed"
    assert data["data"]["value"] == 82.1
    assert data["data"]["refresh_status"] == "upstream_unavailable"


def test_eurostat_one_series_and_locked_import(monkeypatch, tmp_path):
    secret = setup(monkeypatch, tmp_path)
    (dm.BACKUP_DIR / "backup-test").mkdir(parents=True)
    (dm.BACKUP_DIR / "backup-test" / "manifest.json").write_text("{}")
    with patch.object(dm, "fetch_eurostat", return_value=[("2026-08", 2.5)]):
        code, data, _ = request("import", {
            "source": "eurostat", "country": "PT",
            "indicator": "hicp_annual_change_monthly", "mode": "refresh"},
            token=secret)
    assert code == 200 and data["import_status"] == "available"
    assert data["data"]["value"] == 2.5
    assert data["data"]["period"] == "2026-08"

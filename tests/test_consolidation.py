"""Consolidation must not fabricate, overwrite, or import on preview."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from app.country_insights_store import connect, read_indicator, save_result
from scripts import backup_earnwage_data as backup
from scripts import update_country_insights as importer


def test_missing_only_selected_and_dry_run(monkeypatch, tmp_path):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "economic.sqlite3"))
    with connect() as db:
        save_result(db, "PT", "life_expectancy",
                    [{"year": 2024, "value": 82.1}], "available")
    with patch.object(importer, "_fetch",
                      side_effect=AssertionError("Dry run fetched network")):
        preview = importer.run(("PT",), pause=0,
                               indicators=("life_expectancy",
                                           "inflation_annual",
                                           "ppp_private_consumption"),
                               missing_only=True, dry_run=True)
    assert preview["skipped_existing"] == 1
    assert preview["planned"] == 2
    assert preview["available"] == 0
    with connect() as db:
        assert read_indicator(db, "PT", "inflation_annual")["status"] == "not_imported"
        assert read_indicator(db, "PT", "life_expectancy")["value"] == 82.1


def test_targeted_import_keeps_old_observations_on_upstream_failure(
        monkeypatch, tmp_path):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "economic.sqlite3"))
    with connect() as db:
        save_result(db, "PT", "inflation_annual",
                    [{"year": 2023, "value": 4.0}], "available")
    def fetch(_country, _code):
        return ("upstream_unavailable", [], "TimeoutError")
    with patch.object(importer, "_fetch", side_effect=fetch), \
         patch.object(importer.time, "sleep"):
        counts = importer.run(("PT",), pause=0,
                              indicators=("inflation_annual",))
    assert counts["failed"] == 1
    with connect() as db:
        row = read_indicator(db, "PT", "inflation_annual")
    assert row["value"] == 4.0
    assert row["refresh_status"] == "upstream_unavailable"


def test_backup_makes_consistent_separate_db_copies(monkeypatch, tmp_path):
    insights = tmp_path / "insights.sqlite3"
    wages = tmp_path / "wages.sqlite3"
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(insights))
    monkeypatch.setenv("GPP_CACHE_DB", str(wages))
    with sqlite3.connect(insights) as db:
        db.execute("CREATE TABLE known_data(n INTEGER)")
        db.execute("INSERT INTO known_data VALUES (42)")
    with sqlite3.connect(wages) as db:
        db.execute("CREATE TABLE cache_test(n INTEGER)")
        db.execute("INSERT INTO cache_test VALUES (17)")
    monkeypatch.setattr(backup, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "north_america_wages.json").write_text(
        '{"schema":1,"records":[]}', encoding="utf-8")
    target = tmp_path / "private-backups" / "run-001"
    manifest = backup.backup(target)
    assert manifest["databases"]["insights"]["integrity"] == "ok"
    assert manifest["snapshots"]["north_america_wages.json"]["status"] == "backed_up"
    assert manifest["snapshots"]["salaries_snapshot.json"]["status"] == "not_present"
    with sqlite3.connect(target / "insights.sqlite3") as db:
        assert db.execute("SELECT n FROM known_data").fetchone()[0] == 42
    with sqlite3.connect(target / "wages_cache.sqlite3") as db:
        assert db.execute("SELECT n FROM cache_test").fetchone()[0] == 17
    assert json.loads((target / "manifest.json").read_text())[
        "databases"]["wages_cache"]["sha256"] == backup.digest(
            target / "wages_cache.sqlite3")
    with pytest.raises(FileExistsError):
        backup.backup(target)
    with pytest.raises(ValueError):
        backup.backup(tmp_path / "public_html" / "exposed")

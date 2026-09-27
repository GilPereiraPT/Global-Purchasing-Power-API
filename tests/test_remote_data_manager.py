"""Github scheduler: weekdays, two-country bounds and secret safety."""
import pytest

from scripts import remote_data_manager as runner


def test_weekday_rotation_covers_all_world_bank_countries_once():
    countries = [
        code for day in range(7) for code in runner.WORLD_BANK_WEEK[day]
    ]
    assert len(countries) == 14 and len(set(countries)) == 14
    for day in range(7):
        rows = runner.plan(
            "world_bank", "AUTO", essentials=True, weekday=day,
            indicators=("life_expectancy", "inflation_annual",
                        "ppp_private_consumption"))
        assert len(rows) == 4
        assert {x[2] for x in rows} == set(runner.ESSENTIAL)


def test_european_pairs_cover_each_economy_once():
    countries = [code for day in range(7)
                 for code in runner.EUROSTAT_WEEK[day]]
    assert len(countries) == 9 and len(set(countries)) == 9
    assert runner.plan("eurostat", "AUTO", weekday=6) == []


def test_missing_actions_secret_never_connects(monkeypatch):
    monkeypatch.delenv("EARNWAGE_ADMIN_TOKEN", raising=False)
    def never(*args, **kwargs):
        raise AssertionError("Public endpoint must not be used without secret")
    monkeypatch.setattr(runner, "post", never)
    with pytest.raises(RuntimeError, match="Actions secret"):
        runner.main(["--source", "world_bank"])


def test_auto_backup_then_bounded_import(monkeypatch):
    monkeypatch.setenv("EARNWAGE_ADMIN_TOKEN", "a" * 40)
    invoked = []
    def fake_post(token, route, payload=None, timeout=60):
        assert token == "a" * 40
        invoked.append((route, payload))
        if route == "status":
            return {"status": "ok", "backups": [],
                    "indicators": ["life_expectancy", *runner.ESSENTIAL]}
        if route == "backup":
            return {"status": "available", "backup_id": "backup-test"}
        if route == "import":
            return {"import_status": "available"}
        raise AssertionError("Unexpected action")
    monkeypatch.setattr(runner, "post", fake_post)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    assert runner.main(["--source", "world_bank", "--country", "PT",
                        "--mode", "missing", "--essentials"]) == 0
    assert [x[0] for x in invoked] == [
        "status", "backup", "import", "import"]
    assert all(item["country"] == "PT" and item["mode"] == "missing"
               for route, item in invoked if route == "import")


def test_verified_who_uhc_included_in_weekly_automatic_plan():
    indicators = ("life_expectancy", "health_coverage", "gdp_per_capita")
    rows = runner.plan("world_bank", "PT", weekday=0, indicators=indicators)
    assert [item[2] for item in rows] == list(indicators)
    for day in range(7):
        scheduled = runner.plan("world_bank", "AUTO", weekday=day,
                                indicators=indicators)
        assert len([row for row in scheduled if row[2] == "health_coverage"]) == 2

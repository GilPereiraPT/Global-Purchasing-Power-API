"""The public inventory describes stored observations, never guessed coverage."""
import json
import time

from app import data_inventory as inventory
from app import store
from app.country_insights_store import connect as insights_connect, save_result
from app.eurostat_economy import ensure_tables, save as euro_save


def test_inventory_separates_real_sources_and_unimported(monkeypatch, tmp_path):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB",
                       str(tmp_path / "persistent_economic.sqlite3"))
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "wages_and_cache.sqlite3"))
    monkeypatch.setattr(inventory, "load_groups", lambda: [
        {"country": "PT", "isco08_major_group": "5", "period": "2025",
         "unit_type": "local_currency"},
        {"country": "PT", "isco08_major_group": "5", "period": "2025",
         "unit_type": "usd"},  # Must not count as local-currency group wage.
    ])
    with insights_connect() as db:
        save_result(db, "PT", "life_expectancy",
                    [{"year": 2024, "value": 82.38},
                     {"year": 2023, "value": 82.1}], "available")
        save_result(db, "PT", "life_expectancy", [],
                    "upstream_unavailable", "TimeoutError")
        ensure_tables(db)
        euro_save(db, "PT", "hicp_annual_change_monthly",
                  [("2026-08", 3.6)], "available")

    with store.connect() as db:
        from app.ilostat_import import init_salary_db
        from app.north_america import init as na_init
        init_salary_db(db)
        na_init(db)
        db.execute(
            """INSERT INTO salary_observations
            (country,occupation,period,indicator,source_code,classification,
             currency,value,dataset,source_url)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("PT", "cook", "2025", "EARN", "ILOSTAT",
             "ISCO08", "EUR", 1300, "d", "https://example.org"))
        db.execute(
            "INSERT INTO cache(cache_key,response,fetched_at) VALUES (?,?,?)",
            ("ecb:exchange:USD", json.dumps({"period": "2026-09-26",
                                            "source": "ECB"}),
             int(time.time()) - 90000))
        db.commit()
    response = inventory.build_inventory()
    assert response["country_count"] == 14
    pt = next(c for c in response["countries"] if c["code"] == "PT")
    es = next(c for c in response["countries"] if c["code"] == "ES")
    life = pt["world_bank"]["life_expectancy"]
    assert life["value"] == 82.38
    assert life["period"] == 2024
    assert life["observations"] == 2
    assert life["refresh_status"] == "upstream_unavailable"
    assert pt["eurostat_ons_oecd"]["hicp_annual_change_monthly"]["period"] == "2026-08"
    assert es["world_bank"]["life_expectancy"]["status"] == "not_imported"
    assert next(c for c in response["countries"] if c["code"] == "US")[
        "eurostat_ons_oecd"] == {}
    assert pt["exact_occupational_wages"]["occupations"]["cook"]["status"] == "available"
    assert pt["exact_occupational_wages"]["occupations"]["cook"]["sources"][0]["latest_period"] == "2025"
    assert pt["exact_occupational_wages"]["occupations"]["nurse"]["status"] == "not_imported"
    assert pt["ilostat_major_groups"]["5"]["observations"] == 1
    assert response["exchange_rates"]["USD"]["status"] == "expired"
    assert response["summary"]["world_bank"]["available"] == 1
    assert response["summary"]["eurostat_ons_oecd"]["available"] == 1
    assert response["summary"]["exact_occupational_wages"]["observed_pairs"] == 1
    assert response["summary"]["occupation_source_audits"]["audited_countries"] == ["CH", "IT"]
    assert response["summary"]["occupation_source_audits"]["exact_occupation_sources_accepted"] == 0
    ch = next(c for c in response["countries"] if c["code"] == "CH")
    it = next(c for c in response["countries"] if c["code"] == "IT")
    assert ch["occupation_wage_source_audit"]["status"] == "official_group_data_only"
    assert ch["occupation_wage_source_audit"]["ilostat_exact_isco08_4digit_rows"] == 0
    assert it["occupation_wage_source_audit"]["status"] == "official_group_data_only"
    assert it["occupation_wage_source_audit"]["ilostat_exact_isco08_4digit_rows"] == 0
    assert response["summary"]["ilostat_major_groups"]["observed_pairs"] == 1
    assert response["deployment"]["cron_running"] == "not_verifiable_from_http"
    assert "database_path" not in response


def test_wsgi_dispatch_inventory_route_is_read_only(monkeypatch):
    from app import native_wsgi
    sentinel = {"summary": {"world_bank": {"available": 0}}}
    monkeypatch.setattr(inventory, "build_inventory", lambda: sentinel)
    assert native_wsgi.dispatch("/v1/data-inventory", {}) is sentinel

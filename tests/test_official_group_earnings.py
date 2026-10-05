import copy
import json

import pytest

from app.official_group_earnings import catalogue, history, load


def test_api_and_passenger_wsgi_share_published_group_context():
    from fastapi.testclient import TestClient
    from app.main import app
    from tests.test_native_wsgi import request
    with TestClient(app) as client:
        for path, params in (("/v1/pt/earnings/groups", {}),
                             ("/v1/pk/earnings/groups/professionals", {"sex": "women", "period": "2024-25"}),
                             ("/v1/pt/earnings/groups/2", {"period": "2024"}),
                             ("/v1/pk/earnings/groups/doctor", {}),
                             ("/v1/pt/earnings/groups/2", {"period": "2026"})):
            response = client.get(path, params=params)
            status, body, _ = request(path, params)
            assert response.status_code == status
            assert response.json() == body
        inventory = client.get("/v1/data-inventory").json()
        assert inventory["summary"]["official_published_major_groups"]["PK"]["observations"] == 120
        assert inventory["summary"]["ch_bfs_group_context"]["accepted_cells"] == 10020


def test_swiss_published_snapshot_keeps_quality_and_group_precision():
    from collections import Counter
    from app import ch_bfs_wages as ch
    rows = ch.load_snapshot()
    assert Counter(r["quality_status"] for r in rows) == {
        "accepted": 10020, "review_required": 430, "suppressed": 190}
    assert all(r["value"] is None for r in rows if r["source_status"])
    assert len(ch.observed_coverage()) == 40
    value = ch.context("nurse", period="2024")
    assert value["status"] == "available"
    assert value["precision"] == "ch_isco19_submajor_group"
    assert value["attribution"]


def test_published_portuguese_gain_is_independent_group_context():
    data = catalogue("PT")
    assert data["observations"] == 10
    assert data["precision"] == "published_major_occupation_group"
    row = history("PT", "2", period="2024")["observations"][0]
    assert row["value"] == 2395.88
    assert row["measure"] == "mean"
    assert history("PT", "2", sex="women")["status"] == "unavailable"
    with pytest.raises(ValueError):
        history("PT", "doctor")


def test_missing_optional_snapshot_does_not_claim_source_absence(tmp_path):
    missing = tmp_path / "missing.json"
    assert catalogue("PT", missing)["status"] == "not_imported"
    data = history("PK", "professionals", path=missing)
    assert data["status"] == "unavailable" and data["observations"] == []
    assert "not imported" in data["reason"]


def test_pakistani_means_and_medians_keep_sex_and_period():
    assert catalogue("PK")["observations"] == 120
    rows = history("PK", "professionals", "women", "2024-25")["observations"]
    assert {r["measure"]: r["value"] for r in rows} == {"mean": 50660, "median": 53900}
    assert catalogue("PK")["gross_net_basis"] == "not_specified_in_table"
    with pytest.raises(ValueError):
        history("PK", "professionals", period="2024")


@pytest.mark.parametrize("mutation", ["duplicate", "nan", "false_unavailable", "wrong_precision"])
def test_group_snapshot_refuses_misleading_data(tmp_path, mutation):
    data = copy.deepcopy(load("PT"))
    if mutation == "duplicate":
        data["observations"].append(data["observations"][0])
    elif mutation == "nan":
        data["observations"][0]["value"] = float("nan")
    elif mutation == "false_unavailable":
        data["observations"][0]["status"] = "unavailable"
    else:
        data["precision"] = "exact_occupation"
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load("PT", path)

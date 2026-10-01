"""Germany Entgeltatlas state codes and exact-Berufsgattung non-fallback tests."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.de_entgeltatlas_states import STATES, load, wage, coverage, validate
from app.de_entgeltatlas_wages import APPROVED, PRECISION, DEFAULT as NATIONAL_SNAPSHOT


def example():
    occupation = "software_developer"
    page, _national = APPROVED[occupation]
    source = next(r for r in json.loads(NATIONAL_SNAPSHOT.read_text(encoding="utf-8"))["records"]
                  if r["occupation"] == occupation)
    return {
        "occupation": occupation, "state": "BY", "state_ba_region_id": 12,
        "value": 5000, "reference_period": "2025", "currency": "EUR",
        "unit": "EUR/month", "measure": "median", "precision": PRECISION,
        "aggregation_level": "Berufsgattung", "evidence_page_id": page,
        "source_url": "https://web.arbeitsagentur.de/entgeltatlas/beruf/" + page,
        "profession_title": source["profession_title"],
        "occupational_aggregate": source["occupational_aggregate"],
        "requirement_level": source["requirement_level"],
        "raw_ba_evidence_reference": "synthetic-test-only",
    }


def test_region_codes_and_explicit_pending_data():
    assert len(STATES) == 16
    assert STATES["BY"] == ("Bayern", 12)
    assert STATES["NW"] == ("Nordrhein-Westfalen", 8)
    assert load("/unavailable/test-de-entgeltatlas-regions.json") == 0
    assert coverage()["status"] == "pending_verified_regional_import"
    assert coverage()["observed_cells"] == 0
    assert wage("software_developer", "BY")["status"] == "unavailable"
    assert wage("software_developer")["status"] == "not_requested"
    with pytest.raises(ValueError, match="German federal state"):
        wage("software_developer", "FAKE")


def test_validation_strictly_rejects_broad_scope_and_region_substitution():
    row = example()
    obj = {"schema": 1, "country": "DE", "reference_period": "2025",
           "records": [row]}
    assert validate(obj)[("software_developer", "BY")]["value"] == 5000
    for field, bad in (
        ("aggregation_level", "Berufsgruppe"),
        ("occupational_aggregate", "Other occupation, unapproved category"),
        ("state_ba_region_id", 1),
        ("evidence_page_id", "99999999"),
        ("measure", "mean"),
        ("value", 8051),
        ("value", -1),
        ("precision", "ispo_group"),
    ):
        altered = dict(row, **{field: bad})
        with pytest.raises(ValueError):
            validate({**obj, "records": [altered]})
    with pytest.raises(ValueError, match="Duplicate"):
        validate({**obj, "records": [row, row]})


def test_api_exposes_german_states_without_misreporting_unimported_wages():
    with TestClient(app) as client:
        regions = client.get("/v1/regions/DE")
        assert regions.status_code == 200
        options = {r["code"]: r["name"] for r in regions.json()["options"]}
        assert len(options) == 16
        assert options["BY"] == "Bayern"
        result = client.get("/v1/de/entgeltatlas/regional/coverage")
        assert result.status_code == 200
        assert result.json()["observed_cells"] == 0
        res = client.get("/v1/earnwage/overview", params={
            "country": "DE", "occupation": "software_developer", "region": "BY"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["national_occupation_wage"]["status"] == "available"
        assert data["regional_occupation_wage"]["status"] == "unavailable"
        assert data["region"]["selected"] == "BY"
        invalid = client.get("/v1/earnwage/overview", params={
            "country": "DE", "occupation": "software_developer", "region": "NO"
        })
        assert invalid.status_code == 422
        by_country = client.get("/v1/earnwage/coverage").json()["by_country"]
        german = next(row for row in by_country if row["code"] == "DE")
        assert german["regional_salary_coverage"]["observed_occupation_region_pairs"] == 0


def test_brazil_android_card_guard_is_reachable():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "android/app/src/main/java/com/earnwage/app/MainActivity.kt"
    script = path.read_text(encoding="utf-8")
    assert 'code !in listOf("US","CA","BR","DE")' in script
    assert 'if(code=="BR") {' in script
    assert 'if(code=="DE") {' in script

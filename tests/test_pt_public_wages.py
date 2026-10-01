"""Portugal official 2026 public-career entry benchmark: independent from market wages."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.pt_public_wages import CAREERS, CONDITIONAL, DIRECT, coverage, wage

ROOT = Path(__file__).resolve().parents[1]


def test_audited_2026_pt_public_pay_and_precise_scope():
    assert len(DIRECT) == 4
    assert len(CONDITIONAL) == 14
    assert not set(DIRECT).intersection(CONDITIONAL)
    assert CAREERS["assistente_operacional"]["value"] == 934.99
    assert CAREERS["assistente_tecnico"]["value"] == 1035.63
    assert CAREERS["tecnico_superior"]["value"] == 1499.15
    assert CAREERS["enfermeiro"]["value"] == 1657.04
    assert CAREERS["docente"]["value"] == 1770.69
    nurse = wage("nurse")
    assert nurse["value"] == 1657.04
    assert nurse["mapping_precision"] == "direct_public_career"
    assert nurse["observed_national_occupation_wage"] is False
    assert nurse["payment_count_assumed"] is False
    engineer = wage("civil_engineer")
    assert engineer["value"] == 1499.15
    assert engineer["mapping_precision"] == "conditional_comparable_public_career"
    assert engineer["public_role"] == "Técnico superior"
    assert wage("truck_driver")["status"] == "unavailable"


def test_pt_api_keeps_civil_service_comparators_separate_from_market_wages():
    with TestClient(app) as client:
        result = client.get("/v1/earnwage/overview", params={
            "country": "PT", "occupation": "nurse"
        })
        assert result.status_code == 200
        body = result.json()
        assert body["portugal_public_sector_entry"]["value"] == 1657.04
        assert body["portugal_public_sector_entry"]["benchmark_type"] == "public_sector_entry"
        assert body["national_occupation_wage"]["status"] == "unavailable"
        assert body["annual_presentation"]["status"] == "unavailable"
        coverage_api = client.get("/v1/earnwage/coverage")
        assert coverage_api.status_code == 200
        row = next(x for x in coverage_api.json()["by_country"] if x["code"] == "PT")
        assert row["observed_occupations"] == 0
        assert row["public_sector_entry_occupations"] == 18
        endpoint = client.get("/v1/pt/public-sector/coverage")
        assert endpoint.status_code == 200
        assert endpoint.json()["available_benchmarks"] == 18
        other = client.get("/v1/earnwage/overview", params={
            "country": "DE", "occupation": "nurse"
        }).json()
        assert other["portugal_public_sector_entry"]["status"] == "not_applicable"


def test_pt_public_web_snapshot_has_exactly_the_documented_source_mappings():
    data = json.loads((ROOT / "docs/data/pt-public-entry-2026.json").read_text(encoding="utf-8"))
    assert data["schema"] == 1 and data["period"] == "2026"
    assert data["precision"] == "public_sector_entry_not_market_mean"
    assert {key: obj["value"] for key, obj in data["careers"].items()} == {
        key: row["value"] for key, row in CAREERS.items()
    }
    assert {item[0]: item[2] for item in data["occupations"]} == {**DIRECT, **CONDITIONAL}
    assert {item[0]: item[3] for item in data["occupations"]} == {
        **{key: "direct" for key in DIRECT},
        **{key: "conditional" for key in CONDITIONAL},
    }
    page = (ROOT / "docs/portugal.html").read_text(encoding="utf-8")
    main = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert 'fetch("./data/pt-public-entry-2026.json"' in page
    assert 'href="./portugal.html?occupation=nurse"' in main
    assert "não são uma média salarial portuguesa" in page.lower()

def test_pt_40_profession_audit_reports_missing_without_imputation():
    from app.pt_public_wages import occupation_matrix
    matrix = occupation_matrix()
    assert matrix["total_occupations"] == 40
    assert matrix["public_benchmarks"] == 18
    assert matrix["direct_public_career"] == 4
    assert matrix["conditional_comparable_public_career"] == 14
    assert sum(r["public_benchmark_status"] == "unavailable" for r in matrix["rows"]) == 22
    rows = {r["occupation"]: r for r in matrix["rows"]}
    assert rows["nurse"]["mapping_precision"] == "direct_public_career"
    assert rows["nurse"]["value"] == 1657.04
    assert rows["software_developer"]["mapping_precision"] == "conditional_comparable_public_career"
    assert rows["truck_driver"]["value"] is None
    with TestClient(app) as client:
        response = client.get("/v1/pt/public-sector/occupations")
        assert response.status_code == 200
        assert response.json()["rows"] == matrix["rows"]


def test_pt_coverage_table_explains_public_career_vs_broad_group():
    from app.catalog import OCCUPATIONS
    catalog = json.loads((ROOT / "docs/data/pt-coverage-40.json").read_text(encoding="utf8"))
    assert catalog["schema"] == 1
    assert catalog["jobs"] == [[row["id"], row["translations"]["pt"]] for row in OCCUPATIONS]
    webpage = (ROOT / "docs/index.html").read_text(encoding="utf8")
    assert 'id="portugalCoverageDetail"' in webpage or 'host.id="portugalCoverageDetail"' in webpage
    assert 'getPortugalSnapshot()' in webpage
    assert 'fetch("./data/pt-coverage-40.json"' in webpage
    assert 'Grupo ISCO (não é salário da profissão)' in webpage
    assert 'x.public_sector_direct_career_occupations' in webpage

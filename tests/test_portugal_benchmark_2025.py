import io
import json
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.native_wsgi import application
from app.tax_engine import calculate, countries
from app.tax_portugal import SCENARIO


CASES = [
    ("15000", "1153.99", "12196.01", "1016.33"),
    ("25000", "3310.56", "18939.44", "1578.29"),
    ("40000", "8146.61", "27453.39", "2287.78"),
    ("60000", "15471.89", "37928.11", "3160.68"),
    ("100000", "31755.10", "57244.90", "4770.41"),
]


def wsgi(path, params):
    status = []
    body = b"".join(application({
        "PATH_INFO": path,
        "REQUEST_METHOD": "GET",
        "QUERY_STRING": urlencode(params),
        "wsgi.input": io.BytesIO(b""),
    }, lambda code, headers: status.append(int(code.split()[0]))))
    return status[0], json.loads(body)


@pytest.mark.parametrize("gross,irs,net,monthly", CASES)
def test_five_portugal_benchmark_cases(gross, irs, net, monthly):
    result = calculate("PT", gross, 2025, SCENARIO, "mainland", "1000")
    assert result["status"] == "benchmark_estimate"
    assert result["income_tax"] == irs
    assert result["net_income"] == net
    assert result["monthly_equivalent_12"] == monthly
    assert result["calculation_basis"] == "annualized_benchmark_estimate"
    assert "official personal liquidation" in result["reason"].lower()


def test_missing_expenses_withholds_benchmark_net():
    result = calculate("PT", "25000", 2025, SCENARIO, "mainland")
    assert result["status"] == "partial"
    assert result["income_tax"] is None
    assert result["net_income"] is None


def test_metadata_distinguishes_benchmark_from_verified_support():
    registry = countries()
    pt = next(item for item in registry["countries"] if item["country"] == "PT")
    assert pt["supported_tax_years"] == []
    assert pt["benchmark_tax_years"] == [2025]
    assert registry["available_countries"] == []
    assert registry["benchmark_countries"] == ["PT"]


def test_benchmark_components_are_explicit():
    result = calculate("PT", "25000", 2025, SCENARIO, "mainland", "1000")
    components = {item["id"]: item for item in result["components"]}
    assert components["employee_social_security"]["status"] == "benchmark_estimate"
    assert components["employee_social_security"]["value"] == "2750.00"
    assert components["category_a_specific_deduction"]["value"] == "4462.15"
    assert components["taxable_income"]["value"] == "20537.85"
    assert components["general_collection"]["value"] == "3560.56"
    assert components["general_expense_credit"]["value"] == "250.00"
    assert components["other_personal_tax_credits"]["status"] == "benchmark_assumption"


def test_fastapi_and_wsgi_benchmark_parity():
    params = {
        "country": "PT",
        "annual_gross": "25000",
        "tax_year": "2025",
        "scenario": SCENARIO,
        "region": "mainland",
        "eligible_household_expenses": "1000",
    }
    with TestClient(app) as client:
        response = client.get("/v1/tax/calculate", params=params)
    code, body = wsgi("/v1/tax/calculate", params)
    assert response.status_code == code == 200
    assert response.json() == body
    assert body["status"] == "benchmark_estimate"
    assert body["net_income"] == "18939.44"


def test_earnwage_overview_keeps_net_ppp_unavailable():
    params = {
        "country": "PT",
        "occupation": "nurse",
        "annual_gross": "25000",
        "tax_scenario": SCENARIO,
        "tax_region": "mainland",
        "net_tax_year": "2025",
        "eligible_household_expenses": "1000",
    }
    with TestClient(app) as client:
        response = client.get("/v1/earnwage/overview", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["tax_scenario"]["status"] == "benchmark_estimate"
    assert body["tax_scenario"]["net_income"] == "18939.44"
    assert body["net_purchasing_power"]["value"] is None


@pytest.mark.parametrize("changed", [
    {"eligible_household_expenses": "-1"},
    {"eligible_household_expenses": "0.001"},
    {"eligible_household_expenses": "NaN"},
    {"tax_year": "2026"},
    {"region": "azores"},
])
def test_invalid_or_unsupported_requests_do_not_become_benchmark(changed):
    params = {
        "country": "PT",
        "annual_gross": "25000",
        "tax_year": "2025",
        "scenario": SCENARIO,
        "region": "mainland",
        "eligible_household_expenses": "1000",
        **changed,
    }
    with TestClient(app) as client:
        response = client.get("/v1/tax/calculate", params=params)
    if changed.get("eligible_household_expenses") in {"-1", "0.001", "NaN"}:
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        assert response.json()["status"] == "unavailable"

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tax_components import components, marginal, US_SINGLE_BRACKETS


def test_us_2026_brackets_single_and_fica():
    low = components("US", "12400")
    assert low["taxable_income_before_credits"] == 0
    assert low["components"]["federal_income_tax_before_credits"] == 0
    c = components("US", "101420")
    assert c["taxable_income_before_credits"] == 85320
    assert c["components"]["federal_income_tax_before_credits"] == 5800 + (85320-50400)*.22
    assert c["components"]["employee_social_security"] == 6288.04
    assert c["components"]["employee_medicare"] == 1470.59
    assert c["net_income"] is None
    cap = components("US", "250000")["components"]
    assert cap["employee_social_security"] == 11439
    assert cap["employee_additional_medicare"] == 450


def test_ca_2026_cpp_ei_caps():
    c = components("CA", "100000", province="ON")
    comp = c["components"]
    assert comp["employee_cpp_base"] == 3519.45
    assert comp["employee_cpp_first_additional"] == 711
    assert comp["employee_cpp_second_additional"] == 416
    assert comp["employee_employment_insurance"] == 1123.07
    assert c["federal_income_tax"] is None and c["net_income"] is None
    assert components("CA", "100000", province="AB")["status"] == "partial_estimate"


def test_invalid_tax_context_not_relabelled_as_net():
    with pytest.raises(ValueError):
        components("CA", 100000, province="QC")
    with pytest.raises(ValueError):
        components("US", 100000, tax_year=2025)
    with pytest.raises(ValueError):
        components("US", 100000, filing_status="married_joint")
    with pytest.raises(ValueError):
        components("US", -1)
    assert components("PT", 50000)["status"] == "unavailable"


def test_api_tax_components():
    with TestClient(app) as client:
        us = client.get("/v1/tax-components/US?annual_gross=101420")
        assert us.status_code == 200
        assert us.json()["net_income_status"] == "unavailable"
        ca = client.get("/v1/tax-components/CA?annual_gross=100000&province=ON")
        assert ca.status_code == 200
        assert ca.json()["components"]["employee_cpp_second_additional"] == 416
        assert client.get("/v1/tax-components/CA?annual_gross=100000").status_code == 422
        assert client.get("/v1/tax-components/US?annual_gross=0").status_code == 422
        assert client.get("/v1/tax-components/XX?annual_gross=50000").status_code == 404

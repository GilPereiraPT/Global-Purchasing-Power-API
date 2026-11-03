"""Conservative net-PPP rules, with no production DB or external network dependency."""
import pytest

from app.net_purchasing_power import compare_net_ppp


def tax(status="verified", net=20000, gross=30000, currency="EUR", year=2025):
    return {
        "status": status, "net_income": net, "annual_gross": gross,
        "currency": currency, "tax_year": year, "scenario": "single_mainland"
    }


def ppp(status="available"):
    return {
        "status": status, "origin_ppp": 0.5, "destination_ppp": 1,
        "reference_year": 2023
    }


def compare(a=None, b=None, p=None):
    return compare_net_ppp(
        tax() if a is None else a,
        tax(net=60000, gross=90000, currency="CHF") if b is None else b,
        ppp() if p is None else p, ("EUR", "CHF"))


def test_verified_scenarios_net_ppp():
    result = compare()
    assert result["status"] == "verified_models"
    assert result["origin_net_equivalent_in_destination_currency"] == pytest.approx(40000)
    assert result["destination_net_difference_percent"] == pytest.approx(50)
    assert result["tax_year"] == 2025
    assert result["ppp_reference_year"] == 2023


def test_benchmark_status_never_labeled_verified():
    result = compare(a=tax(status="benchmark_estimate"))
    assert result["status"] == "benchmark_estimate"


@pytest.mark.parametrize("status", ["partial", "partial_estimate", "unavailable", "region_needed"])
def test_partial_tax_components_never_imply_net_salary(status):
    result = compare(a=tax(status=status, net=None))
    assert result["status"] == "unavailable"
    assert result["origin_net_equivalent_in_destination_currency"] is None


def test_mismatched_tax_year_refused():
    result = compare(b=tax(net=60000,gross=90000,currency="CHF",year=2024))
    assert result["status"] == "unavailable"
    assert "same explicit tax year" in result["reason"]


def test_missing_ppp_refused():
    assert compare(p=ppp(status="unavailable"))["status"] == "unavailable"


def test_wrong_currency_refused():
    assert compare(a=tax(currency="USD"))["status"] == "unavailable"


@pytest.mark.parametrize("net", [float("nan"),float("inf"),-1,40000,None])
def test_invalid_net_refused(net):
    result=compare(a=tax(net=net))
    assert result["status"] == "unavailable"


def test_zero_net_keeps_safe_null_percentage():
    result=compare(a=tax(net=0))
    assert result["status"] == "verified_models"
    assert result["destination_net_difference_percent"] is None


def test_missing_explicit_tax_scenario():
    result=compare(a={"status":"not_requested","net_income":None})
    assert result["status"] == "unavailable"

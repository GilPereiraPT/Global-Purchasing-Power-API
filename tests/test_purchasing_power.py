"""Regression tests for national gross PPP equivalence; no external network needed."""
import pytest

from app.purchasing_power import calculate_from_observations


def snapshot(values):
    return {"history": [{"year": year, "value": value} for year, value in values],
            "source_url": "https://data.worldbank.org/"}


def calculate(origin, destination, gross=30000, offer=None, a="PT", b="CH"):
    return calculate_from_observations(a, b, gross, offer,
                                       snapshot(origin), snapshot(destination))


def test_latest_common_year_not_latest_individual():
    result = calculate([(2023, .7), (2022, .6)],
                       [(2024, 1.5), (2022, 1.2)])
    assert result["status"] == "available"
    assert result["reference_year"] == 2022
    assert result["value"] == pytest.approx(60000.0)
    assert result["currency"] == "CHF"
    assert result["origin_ppp"] == .6


def test_no_common_reference_year():
    result = calculate([(2023, .7)], [(2022, 1.2)])
    assert result["status"] == "unavailable"
    assert result["value"] is None
    assert result["destination_offer_difference_percent"] is None


def test_invalid_values_and_infinite_values_ignored():
    result = calculate([(2022, -3), (2021, .5)],
                       [(2022, 1.2), (2021, 1)])
    assert result["reference_year"] == 2021
    assert result["value"] == pytest.approx(60000.0)


@pytest.mark.parametrize("amount", [0, -1, float("inf"), float("nan"), 100000001])
def test_invalid_salary_rejected(amount):
    with pytest.raises(ValueError):
        calculate([(2022, .5)], [(2022, 1)], amount)


def test_offer_comparison_is_gross_not_net():
    result = calculate([(2022, .5)], [(2022, 1)], 30000, 90000)
    assert result["value"] == pytest.approx(60000)
    assert result["destination_offer_difference_percent"] == pytest.approx(50)
    assert result["kind"] == "gross_annual_ppp_equivalence"


def test_no_salary_requests_no_equivalence():
    result = calculate([(2022, .5)], [(2022, 1)], None)
    assert result["status"] == "not_requested"
    assert result["value"] is None


def test_same_country_identity_with_same_observation():
    result = calculate([(2022, .7)], [(2022, .7)], 25000, a="PT", b="PT")
    assert result["value"] == pytest.approx(25000)
    assert result["currency"] == "EUR"


def test_no_positive_observations():
    result = calculate([(2022, 0)], [(2022, 1)])
    assert result["status"] == "unavailable"

"""National private-consumption PPP salary equivalence (not a net-pay model).

Only matching-year positive WDI observations from the existing local store are
used.  The unit is local currency per international dollar.  No FX conversion,
tax rate, or city price basket is inferred.
"""
from math import isfinite

from app.catalog import COUNTRY_MAP
from app.country_insights_store import connect, read_indicator

INDICATOR = "ppp_private_consumption"


def calculate_from_observations(country_a, country_b, annual_gross_a,
                                annual_gross_b, origin, destination):
    """Pure function for deterministic tests; records have read_indicator schema."""
    base = {
        "status": "unavailable", "kind": "gross_annual_ppp_equivalence",
        "value": None, "currency": COUNTRY_MAP[country_b]["currency"],
        "reference_year": None, "source": "World Bank World Development Indicators",
        "indicator": INDICATOR,
        "origin_ppp": None, "destination_ppp": None,
        "destination_offer_difference_percent": None,
        "note": ("National private-consumption PPP, not exchange rate, city living "
                 "cost, disposable income, or a personal tax calculation."),
    }
    if annual_gross_a is None:
        return {**base, "status": "not_requested",
                "reason": "Enter an annual gross salary in the origin country's currency."}
    try:
        gross = float(annual_gross_a)
        if not isfinite(gross) or not 0 < gross <= 100_000_000:
            raise ValueError()
        offered = None if annual_gross_b is None else float(annual_gross_b)
        if offered is not None and (not isfinite(offered) or not 0 < offered <= 100_000_000):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Annual gross salaries must be positive finite amounts up to 100000000.")

    def valid_history(record):
        return {int(x["year"]): float(x["value"])
                for x in record.get("history", [])
                if isinstance(x, dict)
                and type(x.get("year")) is int and 1960 <= x["year"] <= 2100
                and type(x.get("value")) in (int, float)
                and isfinite(x["value"]) and x["value"] > 0}
    a = valid_history(origin)
    b = valid_history(destination)
    common = a.keys() & b.keys()
    if not common:
        return {**base, "reason": "No positive private-consumption PPP observations for a common reference year.",
                "source_urls": [origin.get("source_url"), destination.get("source_url")]}
    year = max(common)
    equivalent = gross * b[year] / a[year]
    if not isfinite(equivalent):
        return {**base, "reason": "PPP equivalence exceeds numeric limits."}
    result = {**base, "status": "available", "value": equivalent,
              "reference_year": year, "origin_ppp": a[year],
              "destination_ppp": b[year],
              "origin_currency": COUNTRY_MAP[country_a]["currency"],
              "source_urls": [origin.get("source_url"), destination.get("source_url")]}
    if offered is not None and equivalent > 0:
        result["destination_offer_difference_percent"] = (offered / equivalent - 1) * 100
        result["destination_offer_annual_gross"] = offered
    return result


def compare(country_a, country_b, annual_gross_a=None, annual_gross_b=None):
    """Read-only snapshot lookup; never contacts World Bank on a user request."""
    if country_a not in COUNTRY_MAP or country_b not in COUNTRY_MAP:
        raise LookupError("Unknown country")
    if annual_gross_a is None:
        return calculate_from_observations(country_a, country_b, None, annual_gross_b, {}, {})
    with connect() as db:
        origin = read_indicator(db, country_a, INDICATOR, history=True)
        destination = (origin if country_a == country_b else
                       read_indicator(db, country_b, INDICATOR, history=True))
    return calculate_from_observations(country_a, country_b, annual_gross_a,
                                       annual_gross_b, origin, destination)

"""Compare after-tax purchasing power only for explicit, sufficiently supported tax scenarios.

Never convert partial payroll components into a net salary, and never infer tax
residence from the job advertisement location.
"""
from math import isfinite

VALID_STATUSES = {"verified", "benchmark_estimate"}


def compare_net_ppp(origin_tax, destination_tax, gross_ppp, expected_currencies):
    """Compute net PPP equivalence only when both net tax outcomes are usable."""
    base = {
        "status": "unavailable",
        "kind": "annual_net_ppp_comparison",
        "origin_net_income": None,
        "destination_net_income": None,
        "origin_net_equivalent_in_destination_currency": None,
        "destination_net_difference_percent": None,
        "currency": expected_currencies[1],
        "ppp_reference_year": None,
        "tax_year": None,
        "note": ("This is an indicative comparison of annual net incomes using "
                 "national private-consumption PPP, not a personal financial "
                 "forecast or a city-level cost-of-living estimate."),
    }
    if not isinstance(origin_tax, dict) or not isinstance(destination_tax, dict):
        return {**base, "reason": "Both explicit tax scenarios are required."}
    if gross_ppp.get("status") != "available":
        return {**base, "reason": "Compatible national PPP observations are not available."}
    if (origin_tax.get("status") not in VALID_STATUSES or
            destination_tax.get("status") not in VALID_STATUSES):
        return {**base, "reason": "One or both tax scenarios are incomplete or unavailable."}
    a_year = origin_tax.get("tax_year")
    b_year = destination_tax.get("tax_year")
    if type(a_year) is not int or a_year != b_year:
        return {**base, "reason": "Tax scenarios must use the same explicit tax year."}
    if (origin_tax.get("currency") != expected_currencies[0] or
            destination_tax.get("currency") != expected_currencies[1]):
        return {**base, "reason": "Tax scenario currency does not match the selected country."}
    if (origin_tax.get("annual_gross") is None or
            destination_tax.get("annual_gross") is None):
        return {**base, "reason": "Both scenarios need an annual gross salary."}
    try:
        net_a = float(origin_tax["net_income"])
        net_b = float(destination_tax["net_income"])
        gross_a = float(origin_tax["annual_gross"])
        gross_b = float(destination_tax["annual_gross"])
        factor_a = float(gross_ppp["origin_ppp"])
        factor_b = float(gross_ppp["destination_ppp"])
        if not (all(isfinite(v) for v in (net_a, net_b, gross_a, gross_b, factor_a, factor_b))
                and net_a >= 0 and net_b >= 0 and gross_a > 0 and gross_b > 0
                and net_a <= gross_a and net_b <= gross_b and factor_a > 0 and factor_b > 0):
            raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError):
        return {**base, "reason": "Tax or PPP results contain invalid monetary amounts."}
    equivalent = net_a * factor_b / factor_a
    if not isfinite(equivalent):
        return {**base, "reason": "Net PPP equivalent exceeds numeric limits."}
    # A percentage requires a nonzero reference net equivalence.
    difference = ((net_b / equivalent - 1) * 100
                  if equivalent > 0 else None)
    if difference is not None and not isfinite(difference):
        difference = None
    status = ("verified_models" if origin_tax["status"] == destination_tax["status"] == "verified"
              else "benchmark_estimate")
    return {**base, "status": status,
            "origin_net_income": net_a, "destination_net_income": net_b,
            "origin_net_equivalent_in_destination_currency": equivalent,
            "destination_net_difference_percent": difference,
            "ppp_reference_year": gross_ppp["reference_year"],
            "tax_year": a_year,
            "tax_model_statuses": [origin_tax["status"], destination_tax["status"]],
            "origin_scenario": origin_tax.get("scenario"),
            "destination_scenario": destination_tax.get("scenario"),
            "assumptions": ["Annual net model results; not actual payslip amounts",
                            "National PPP levels; not a city cost-of-living basket",
                            "Tax residence, household circumstances and coverage must be reviewed"],
            "reason": None}

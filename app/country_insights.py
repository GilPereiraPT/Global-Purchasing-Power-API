"""EarnWage country insights: sourced World Bank observations, no invented values.

This module does not calculate an EarnWage quality-of-life score.
Gallup Law and Order data are not fetched/scraped without a redistribution licence.
"""
import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ISO3 = {
    "PT": "PRT", "ES": "ESP", "DE": "DEU", "FR": "FRA",
    "GB": "GBR", "IE": "IRL", "NL": "NLD", "CH": "CHE",
    "IT": "ITA", "US": "USA", "CA": "CAN", "BR": "BRA",
    "IN": "IND", "PK": "PAK",
}
INDICATORS = {
    "life_expectancy": ("SP.DYN.LE00.IN", "years"),
    "unemployment": ("SL.UEM.TOTL.ZS", "percent_of_labor_force"),
    "gini": ("SI.POV.GINI", "index_0_100"),
    "health_coverage": ("SH.UHC.SRVS.CV.XD", "index_0_100"),
    "primary_completion": ("SE.PRM.CMPT.ZS", "percent_of_relevant_age_group"),
    "adult_literacy": ("SE.ADT.LITR.ZS", "percent_of_adults_15_plus"),
    "electricity_access": ("EG.ELC.ACCS.ZS", "percent_of_population"),
    "safe_drinking_water": ("SH.H2O.SMDW.ZS", "percent_of_population"),
    "safe_sanitation": ("SH.STA.SMSS.ZS", "percent_of_population"),
    "internet_use": ("IT.NET.USER.ZS", "percent_of_population"),
}
SOURCE = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=1000"
CACHE_SECONDS = 86400
_CACHE = {}
_LOCK = threading.Lock()


def _fetch(country, indicator):
    key = (country, indicator)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and time.time() - cached[0] < CACHE_SECONDS:
            return cached[1]
    url = SOURCE.format(country=quote(ISO3[country]),
                        indicator=quote(indicator))
    request = Request(url, headers={"User-Agent": "EarnWage/0.5 CountryInsights",
                                    "Accept": "application/json"})
    try:
        with urlopen(request, timeout=9) as response:
            payload = json.load(response)
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("Unexpected World Bank response")
        observations = [
            {"year": int(row["date"]), "value": float(row["value"])}
            for row in payload[1]
            if isinstance(row, dict) and row.get("value") is not None
            and str(row.get("date", "")).isdigit()
        ]
        observations.sort(key=lambda item: item["year"], reverse=True)
        result = ("available", observations, None)
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError, OSError) as exc:
        result = ("upstream_unavailable", [], type(exc).__name__)
    with _LOCK:
        _CACHE[key] = (time.time(), result)
    return result


def indicator(country, name, year=None, history=False):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    if name not in INDICATORS:
        raise ValueError("Unknown indicator")
    if year is not None and (not isinstance(year, int) or not 1960 <= year <= 2100):
        raise ValueError("Invalid year")
    code, unit = INDICATORS[name]
    status, observations, error = _fetch(country, code)
    matching = [row for row in observations if year is None or row["year"] == year]
    row = matching[0] if matching else None
    result = {
        "country": country, "iso3": ISO3[country], "name": name,
        "indicator_code": code, "unit": unit,
        "status": "available" if row else ("unavailable" if status == "available" else status),
        "value": row["value"] if row else None,
        "year": row["year"] if row else None,
        "requested_year": year,
        "source": "World Bank World Development Indicators",
        "source_url": SOURCE.format(country=ISO3[country], indicator=code),
        "note": "Latest non-null observation; years may differ across countries and indicators. No interpolation.",
    }
    if history:
        result["history"] = matching
    if error:
        result["error_type"] = error
    return result


def safety(country):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    return {
        "country": country, "status": "unavailable", "value": None, "year": None,
        "name": "Gallup Law and Order Index",
        "unit": "index_0_100",
        "source": "Gallup World Poll",
        "source_url": "https://www.gallup.com/analytics/694904/what-is-law-order-index.aspx",
        "reason": "Automated licensed country-level dataset not yet connected; do not substitute homicide rates or scrape Gallup.",
        "alternative": {
            "name": "Feeling safe walking alone after dark",
            "sdg_indicator": "16.1.4",
            "sdg_series": "VC_SNS_WALN_DRK",
            "source_url": "https://unstats.un.org/sdgs/metadata/files/Metadata-16-01-04.pdf",
            "status": "not_connected",
        },
    }


def country_insights(country):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    result = {name: indicator(country, name) for name in INDICATORS}
    result["safety"] = safety(country)
    return {"country": country, "iso3": ISO3[country], "indicators": result,
            "note": "Independent official indicators, not a composite EarnWage score or personal access guarantee."}

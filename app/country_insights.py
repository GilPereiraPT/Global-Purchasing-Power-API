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
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "USD_current_per_person"),
    "gini": ("SI.POV.GINI", "index_0_100"),
    "health_coverage": ("SH.UHC.SRVS.CV.XD", "index_0_100"),
    "primary_completion": ("SE.PRM.CMPT.ZS", "percent_of_relevant_age_group"),
    "adult_literacy": ("SE.ADT.LITR.ZS", "percent_of_adults_15_plus"),
    "electricity_access": ("EG.ELC.ACCS.ZS", "percent_of_population"),
    "safe_drinking_water": ("SH.H2O.SMDW.ZS", "percent_of_population"),
    "safe_sanitation": ("SH.STA.SMSS.ZS", "percent_of_population"),
    "internet_use": ("IT.NET.USER.ZS", "percent_of_population"),
    "inflation_annual": ("FP.CPI.TOTL.ZG", "annual_percent"),
    "ppp_private_consumption": ("PA.NUS.PRVT.PP", "local_currency_units_per_international_dollar"),
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
        with urlopen(request, timeout=15) as response:
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
    """Serve only locally imported data; never call the World Bank on HTTP."""
    from app.country_insights_store import connect, read_indicator
    with connect() as db:
        return read_indicator(db, country, name, year=year, history=history)


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
    from app.country_insights_store import connect, read_indicator
    with connect() as db:
        result = {name: read_indicator(db, country, name) for name in INDICATORS}
    result["safety"] = safety(country)
    return {"country": country, "iso3": ISO3[country], "indicators": result,
            "note": "Locally cached independent official indicators; no live World Bank calls, composite score or personal access guarantee."}

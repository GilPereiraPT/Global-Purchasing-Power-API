"""Observed exact-occupation annual history; never substitute ISCO major groups."""
import re

from app.store import connect
from app import north_america as na
from app import uk_ashe_wages as uk
from app import de_entgeltatlas_wages as de
from app import fr_insee_wages as fr
from app import nl_cbs_wages as nl
from app.ilostat_import import init_salary_db


def observation_year(period):
    """Retain year-first periods and recognize BLS English month/year labels."""
    text = str(period)
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    match = re.fullmatch(
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})",
        text,
    )
    if match:
        return int(match.group(1))
    raise ValueError("Unsupported observation period")


def exact_history(country, occupation, start_year, end_year):
    if country in ("US", "CA"):
        with connect() as db:
            na.init(db)
            rows = db.execute(
                """SELECT reference_period, published_year, currency, measure, unit,
                          value, source, source_url, classification
                   FROM north_america_wages WHERE country=? AND occupation=?""",
                (country, occupation)).fetchall()
        entries = []
        for period, published, currency, measure, unit, value, source, url, classification in rows:
            try:
                year = observation_year(period)
            except ValueError:
                continue
            if start_year <= year <= end_year:
                entries.append({"year":year, "published_year":published,
                                "reference_period":period,
                                "currency":currency, "measure":measure, "unit":unit,
                                "value":value, "source":source, "source_url":url,
                                "classification":classification})
    elif country == "GB":
        with connect() as db:
            uk.init(db)
            rows = db.execute(
                """SELECT reference_period,published_year,currency,measure,unit,
                          value,source,source_url,classification
                   FROM uk_ashe_wages WHERE country='GB' AND occupation=?""",
                (occupation,)).fetchall()
        entries = []
        for period,published,currency,measure,unit,value,source,url,classification in rows:
            try:
                year=int(str(period)[:4])
            except ValueError:
                continue
            if start_year <= year <= end_year:
                entries.append({"year":year,"published_year":published,
                                "currency":currency,"measure":measure,"unit":unit,
                                "value":value,"source":source,"source_url":url,
                                "classification":classification})
    elif country == "DE" and occupation in de.APPROVED:
        with connect() as db:
            de.init(db)
            rows = db.execute(
                """SELECT reference_period,currency,measure,unit,value,source,
                          source_url,evidence_page_id
                   FROM de_entgeltatlas_wages
                   WHERE country='DE' AND occupation=?""",
                (occupation,)).fetchall()
        entries = []
        for period,currency,measure,unit,value,source,url,page_id in rows:
            try:
                year = int(str(period)[:4])
            except ValueError:
                continue
            if start_year <= year <= end_year:
                entries.append({"year":year, "currency":currency,
                                "measure":measure, "unit":unit, "value":value,
                                "source":source, "source_url":url,
                                "classification":"BA-Entgeltatlas:"+page_id})
    elif country == "FR" and occupation in fr.APPROVED:
        with connect() as db:
            fr.init(db)
            rows = db.execute(
                """SELECT reference_period,currency,measure,unit,value,source,
                          source_url,pcs_ese
                   FROM fr_insee_wages
                   WHERE country='FR' AND occupation=?""",
                (occupation,)).fetchall()
        entries = []
        for period,currency,measure,unit,value,source,url,pcs in rows:
            try:
                year = int(str(period)[:4])
            except ValueError:
                continue
            if start_year <= year <= end_year:
                entries.append({"year":year, "currency":currency,
                                "measure":measure, "unit":unit, "value":value,
                                "source":source, "source_url":url,
                                "classification":"PCS-ESE 2003:"+pcs})
    elif country == "NL" and occupation in nl.APPROVED:
        with connect() as db:
            nl.init(db)
            rows = db.execute(
                """SELECT reference_period,currency,measure,unit,value,source,
                          source_url,brc_code,publication_status,precision
                   FROM nl_cbs_wages
                   WHERE country='NL' AND occupation=?""",
                (occupation,)).fetchall()
        entries = []
        for period,currency,measure,unit,value,source,url,brc_code,publication_status,precision in rows:
            try:
                year = int(str(period)[:4])
            except ValueError:
                continue
            if start_year <= year <= end_year:
                entries.append({"year":year, "currency":currency,
                                "measure":measure, "unit":unit, "value":value,
                                "source":source, "source_url":url,
                                "classification":"BRC 2014 editie 2025:"+brc_code,
                                "reference_period":period, "publication_status":publication_status,
                                "precision":precision})
    else:
        with connect() as db:
            init_salary_db(db)
            rows = db.execute(
                """SELECT period,currency,value,source_code,source_url,classification
                   FROM salary_observations WHERE country=? AND occupation=?
                   AND period>=? AND period<=?""",
                (country, occupation, str(start_year), str(end_year))).fetchall()
        entries = [{"year":int(period), "currency":currency, "measure":"mean",
                    "unit":currency+"/month", "value":value, "source":"ILOSTAT",
                    "source_code":source, "source_url":url, "classification":classification}
                   for period,currency,value,source,url,classification in rows]
    observations = []
    for year in range(start_year, end_year+1):
        candidates = [e for e in entries if e["year"] == year]
        annual = [e for e in candidates if e["unit"] == e["currency"]+"/year"]
        monthly = [e for e in candidates if e["unit"] == e["currency"]+"/month"]
        hourly = [e for e in candidates if e["unit"] == e["currency"]+"/hour"]
        selected = annual if annual else monthly if monthly else hourly
        preferred_measure = "median" if country in ("GB", "DE", "NL") else "mean"
        preferred = [e for e in selected if e["measure"] == preferred_measure]
        if preferred:
            selected = preferred
        if len(selected) == 1:
            e = selected[0]
            is_hourly = e["unit"].endswith("/hour")
            is_annual = e["unit"].endswith("/year")
            if is_hourly:
                observations.append({
                    "year":year, "status":"available",
                    "annual_presentation":{
                        "status":"unavailable", "value":None, "unit":"per_year",
                        "reason":"Only a verified hourly wage is available; annual working hours are not assumed."
                    },
                    "reported_hourly":{
                        "status":"available", "value":e["value"],
                        "currency":e["currency"], "unit":"per_hour",
                        "kind":"reported_hourly", "reference_period":e.get("reference_period", str(year)),
                        "source":e["source"], "measure":e["measure"],
                        "precision":e.get("precision", "exact_occupation")
                    },
                    "source_observations":candidates,
                })
                continue
            value = e["value"] if is_annual else round(e["value"]*12, 6)
            display = {"status":"available", "value":value,
                       "currency":e["currency"], "unit":"per_year",
                       "kind":"reported_annual" if is_annual else "annualized_12_month_equivalent",
                       "reference_period":e.get("reference_period", str(year)), "source":e["source"],
                       "measure":e["measure"], "monthly_optional":value/12 if is_annual else e["value"],
                       "monthly_kind":"annual_divided_by_12" if is_annual else "reported_monthly",
                       "payments_per_year":None, "payments_verified":False,
                       "precision":"exact_occupation",
                       "note":"No contractual extra payments inferred; annualized monthly earnings are not verified total annual remuneration."}
            status = "available"
        elif selected:
            display = {"status":"ambiguous", "value":None, "unit":"per_year",
                       "reason":"Multiple observations for the same measure and year; no arbitrary source selected"}
            status = "ambiguous"
        else:
            display = {"status":"unavailable", "value":None, "unit":"per_year",
                       "reason":"No observed annual or monthly exact-occupation wage for this year"}
            status = "unavailable"
        observations.append({"year":year, "status":status, "annual_presentation":display,
                             "source_observations":candidates})
    return {"country":country, "occupation":occupation,
            "precision":nl.PRECISION if country == "NL" and occupation in nl.APPROVED else "exact_occupation",
            "start_year":start_year, "end_year":end_year,
            "observations":observations,
            "note":("Only imported approved CBS occupational-group observations; hourly wages are not annualized without validated hours."
                    if country == "NL" and occupation in nl.APPROVED else
                    "Only imported exact-occupation observations; hourly-only observations are not annualized without validated hours.")}

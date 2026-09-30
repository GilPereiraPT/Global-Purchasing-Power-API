"""Verified wage observations for North America; units are NEVER silently annualized.

Canada: official Job Bank 2025 open-data CSV. US: administrator-downloaded BLS
May 2025 national OEWS workbook (the BLS website may block automated downloads).
Neither source is an API-key-paid service; ingestion is offline.
"""
import argparse
import csv
import io
import json
import math
import re
from pathlib import Path

import httpx

from app.store import connect

CANADA_URL = (
    "https://open.canada.ca/data/dataset/adad580f-76b0-4502-bd05-20c125de9116/"
    "resource/9da94d63-b178-4a64-aeb3-b6a3bd721ad2/download/"
    "2a71-das-wage2025opendata-esdc-all-19nov2025-vf.csv"
)
CANADA_DATASET = "Job Bank 2025 Wages (published 2025-11-19)"
BLS_DATASET = "BLS May 2025 OEWS national"
BLS_TABLE = "https://www.bls.gov/oes/tables.htm"
BLS_NEWS_TABLE = "https://www.bls.gov/news.release/ocwage.t01.htm"
# Verified matches to NOC 2021 unit groups. Broad/ambiguous job names stay absent.
CANADA_NOC = {
    "accountant": ("11100", "Financial auditors and accountants"),
    "auditor": ("11100", "Financial auditors and accountants"),
    "doctor": ("31102", "General practitioners and family physicians"),
    "it_technician": ("22221", "User support technicians"),
    "data_analyst": ("21223", "Database analysts and data administrators"),
    "warehouse_operator": ("75101", "Material handlers"),
    "automotive_mechanic": ("72410", "Automotive service technicians"),
    "supermarket_worker": ("65100", "Cashiers"),
    "waiter": ("65200", "Food and beverage servers"),
    "industrial_operator": ("95109", "Other labourers in processing, manufacturing and utilities"),
    "nurse": ("31301", "Registered nurses"),
    "civil_engineer": ("21300", "Civil engineers"),
    "electrician": ("72200", "Electricians"),
    "physiotherapist": ("31202", "Physiotherapists"),
    # These NOC 2021 titles were checked against the actual 2025 Job Bank CSV.
    "financial_analyst": ("11101", "Financial and investment analysts"),
    "administrative_assistant": ("13110", "Administrative assistants"),
    "receptionist": ("14101", "Receptionists"),
    "architect": ("21200", "Architects"),
    "cybersecurity_specialist": ("21220", "Cybersecurity specialists"),
    "software_developer": ("21232", "Software developers and programmers"),
    "mechanical_engineer": ("21301", "Mechanical engineers"),
    "pharmacist": ("31120", "Pharmacists"),
    "psychologist": ("31200", "Psychologists"),
    "dentist": ("31110", "Dentists"),
    "secondary_teacher": ("41220", "Secondary school teachers"),
    "cook": ("63200", "Cooks"),
    "sales_assistant": ("64100", "Retail salespersons and visual merchandisers"),
    "security_guard": ("64410", "Security guards and related security service occupations"),
    "cleaner": ("65310", "Light duty cleaners"),
    "welder": ("72106", "Welders and related machine operators"),
    "plumber": ("72300", "Plumbers"),
    "truck_driver": ("73300", "Transport truck drivers"),
    "bus_driver": ("73301", "Bus drivers, subway operators and other transit operators"),
    "construction_worker": ("75110", "Construction trades helpers and labourers"),
    "lawyer": ("41101", "Lawyers and Quebec notaries"),
    "healthcare_assistant": ("33102", "Nurse aides, orderlies and patient service associates"),
    "preschool_teacher": ("42202", "Early childhood educators and assistants"),
    "teacher": ("41221", "Elementary school and kindergarten teachers"),
}
# US SOC 2018 detailed units. Avoid conflating related-but-distinct occupations.
US_SOC = {
    "accountant": ("13-2011", "Accountants and Auditors"),
    "nurse": ("29-1141", "Registered Nurses"),
    "civil_engineer": ("17-2051", "Civil Engineers"),
    "electrician": ("47-2111", "Electricians"),
    "software_developer": ("15-1252", "Software Developers"),
    "mechanical_engineer": ("17-2141", "Mechanical Engineers"),
    "pharmacist": ("29-1051", "Pharmacists"),
    "physiotherapist": ("29-1123", "Physical Therapists"),
    "dentist": ("29-1021", "Dentists, General"),
    "cybersecurity_specialist": ("15-1212", "Information Security Analysts"),
}


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS north_america_wages (
        country TEXT NOT NULL, occupation TEXT NOT NULL, geography TEXT NOT NULL,
        classification TEXT NOT NULL, job_title TEXT NOT NULL, reference_period TEXT NOT NULL,
        published_year INTEGER NOT NULL, currency TEXT NOT NULL,
        measure TEXT NOT NULL, unit TEXT NOT NULL, value REAL NOT NULL,
        source TEXT NOT NULL, source_url TEXT NOT NULL,
        PRIMARY KEY(country,occupation,geography,classification,reference_period,measure,source)
    )""")


def number(raw):
    try:
        v = float(str(raw).strip().replace(",", ""))
        return v if math.isfinite(v) and 0 < v < 1e12 else None
    except (ValueError, TypeError):
        return None


def canada_records(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    required = {
        "NOC_CNP", "NOC_Title_eng", "prov", "ER_Code_Code_RE",
        "Median_Wage_Salaire_Median", "Average_Wage_Salaire_Moyen",
        "Annual_Wage_Flag_Salaire_annuel", "Reference_Period",
    }
    if not required <= set(reader.fieldnames or []):
        raise ValueError("Unexpected official Canada wage CSV schema")
    mapped = {}
    for key, (noc, title) in CANADA_NOC.items():
        mapped.setdefault(f"NOC_{noc}", []).append((key, title))
    count = 0
    for row in reader:
        code = row["NOC_CNP"]
        if code not in mapped or row["prov"] != "NAT" or row["ER_Code_Code_RE"] != "ER00":
            continue
        period = row["Reference_Period"]
        if not period or period.upper() in ("NA", "N/A"):
            continue
        flag = row["Annual_Wage_Flag_Salaire_annuel"]
        if flag not in ("0", "1"):
            continue
        unit = "CAD/year" if flag == "1" else "CAD/hour"
        for key, expected in mapped[code]:
            if not row["NOC_Title_eng"].casefold().startswith(expected.casefold()):
                raise ValueError(f"NOC title drift for {code}: {row['NOC_Title_eng']}")
            for measure, column in (
                ("median", "Median_Wage_Salaire_Median"),
                ("mean", "Average_Wage_Salaire_Moyen"),
            ):
                value = number(row[column])
                if value is None:
                    continue
                count += 1
                yield ("CA", key, "national", f"NOC2021:{code.removeprefix('NOC_')}", row["NOC_Title_eng"],
                       period, 2025, "CAD", measure, unit, value,
                       CANADA_DATASET, CANADA_URL)
    if count == 0:
        raise ValueError("No eligible national occupation wages in Canadian CSV")


def us_records(path, year):
    """BLS XLSX: details must be NATIONAL and SOC detailed, no region conflation."""
    from openpyxl import load_workbook
    if year < 2020 or year > 2100:
        raise ValueError("Invalid publication year")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        it = sheet.iter_rows(values_only=True)
        headers = [str(x).strip().upper() if x is not None else "" for x in next(it)]
        required = {"OCC_CODE", "OCC_TITLE", "A_MEAN", "AREA"}
        if not required <= set(headers):
            raise ValueError("Unexpected BLS OEWS workbook columns")
        mapped = {soc: (job, title) for job, (soc, title) in US_SOC.items()}
        count = 0
        for values in it:
            row = dict(zip(headers, values))
            code = str(row.get("OCC_CODE") or "").strip()
            if code not in mapped or str(row.get("AREA") or "").strip() not in ("99", "99.0"):
                continue
            job, title = mapped[code]
            if str(row["OCC_TITLE"]).casefold().strip() != title.casefold():
                raise ValueError(f"SOC title drift for {code}")
            if "O_GROUP" in headers and str(row.get("O_GROUP") or "").lower() != "detailed":
                continue
            for measure, column in (("mean", "A_MEAN"), ("median", "A_MEDIAN")):
                if column not in row:
                    continue
                value = number(row[column])
                if value is None:
                    continue
                count += 1
                yield ("US", job, "national", f"SOC2018:{code}", title, str(year),
                       year, "USD", measure, "USD/year", value, BLS_DATASET, BLS_TABLE)
        if not count:
            raise ValueError("No eligible BLS national detailed occupation observations")
    finally:
        workbook.close()


COLUMNS = (
    "country", "occupation", "geography", "classification", "job_title",
    "reference_period", "published_year", "currency", "measure", "unit",
    "value", "source", "source_url",
)


def persist(records):
    count = 0
    with connect() as db:
        init(db)
        for record in records:
            db.execute("INSERT OR REPLACE INTO north_america_wages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       record)
            count += 1
        if count == 0:
            raise ValueError("No validated observations; refusing empty import")
        db.commit()
    return count


def import_canada():
    response = httpx.get(CANADA_URL, timeout=90, follow_redirects=True)
    response.raise_for_status()
    if len(response.content) > 25_000_000:
        raise ValueError("Official Canadian CSV unexpectedly large")
    return persist(canada_records(response.content.decode("utf-8-sig")))


def observed_coverage():
    """Compact country/occupation coverage for the full availability matrix."""
    with connect() as db:
        init(db)
        rows = db.execute("""SELECT country,occupation,MAX(reference_period)
            FROM north_america_wages GROUP BY country,occupation""").fetchall()
    return {(country, occupation): period for country, occupation, period in rows}


def wages(country, occupation):
    if country not in ("US", "CA"):
        return {"status": "unavailable", "country": country, "occupation": occupation,
                "reason": "No North American wage source for selected country"}
    with connect() as db:
        init(db)
        rows = db.execute("""SELECT geography, classification, job_title,
          reference_period, published_year, currency, measure, unit, value, source, source_url
          FROM north_america_wages WHERE country=? AND occupation=?
          ORDER BY published_year DESC, reference_period DESC, measure""",
          (country, occupation)).fetchall()
    if not rows:
        return {"status": "unavailable", "country": country, "occupation": occupation,
                "reason": "No validated occupational observation imported"}
    newest = (rows[0][4], rows[0][3])
    subset = [r for r in rows if (r[4], r[3]) == newest]
    return {"status": "available", "country": country, "occupation": occupation,
            "geography": "national", "published_year": newest[0],
            "reference_period": newest[1],
            "observations": [dict(zip(
                ("geography", "classification", "job_title", "reference_period",
                 "published_year", "currency", "measure", "unit", "value", "source", "source_url"), r
            )) for r in subset],
            "note": "The source unit and statistical measure are retained; no gross-to-net or hourly-to-monthly inference."}


def export_snapshot(path="data/north_america_wages.json"):
    with connect() as db:
        init(db)
        rows = db.execute("""SELECT country,occupation,geography,classification,
          job_title,reference_period,published_year,currency,measure,unit,value,
          source,source_url FROM north_america_wages ORDER BY country,occupation,measure""").fetchall()
    if not rows:
        raise ValueError("No verified records to export")
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"schema": 1, "records":
                      [dict(zip(COLUMNS, r)) for r in rows]}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return len(rows)


def load_snapshot(path):
    path = Path(path)
    if not path.exists():
        return 0
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != 1 or not isinstance(obj.get("records"), list):
        raise ValueError("Invalid North America snapshot")
    validated = []
    for r in obj["records"]:
        if r["country"] == "CA":
            mapping, prefix, currency = CANADA_NOC, "NOC2021:", "CAD"
        elif r["country"] == "US":
            mapping, prefix, currency = US_SOC, "SOC2018:", "USD"
        else:
            raise ValueError("Invalid snapshot country")
        entry = mapping.get(r["occupation"])
        if not entry or r["classification"] != prefix + entry[0] or r["currency"] != currency:
            raise ValueError("Invalid occupation classification or currency")
        if r["measure"] not in ("mean", "median") or r["unit"] not in (currency + "/hour", currency + "/year"):
            raise ValueError("Invalid wage units")
        if number(r["value"]) is None or r["geography"] != "national":
            raise ValueError("Invalid wage observation")
        validated.append(tuple(r[k] for k in COLUMNS))
    if not validated:
        return 0
    return persist(validated)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--canada", action="store_true")
    group.add_argument("--us-xlsx", metavar="FILE")
    group.add_argument("--export", action="store_true")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    if args.canada:
        print(json.dumps({"source": CANADA_URL, "imported": import_canada()}))
    elif args.us_xlsx:
        print(json.dumps({"source": BLS_TABLE,
                          "imported": persist(us_records(args.us_xlsx, args.year))}))
    else:
        print(json.dumps({"exported": export_snapshot()}))


if __name__ == "__main__":
    main()

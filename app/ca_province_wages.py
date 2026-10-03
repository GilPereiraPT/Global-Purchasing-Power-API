"""Canadian Job Bank 2025 province/territory wage observations.

Separate snapshot/database to preserve the existing national North America
schema and avoid confusing economic regions with province-wide statistics.
"""
import csv
import io
import json
from pathlib import Path
from app.store import connect
from app.client_config import REGIONS
from app.north_america import CANADA_NOC, CANADA_URL, CANADA_DATASET, number

PROVINCES = {code: name for code, name in REGIONS["CA"]["options"]}
# Official Job Bank 2025 province codes and province-wide economic-region totals.
# PEI, YK and NWT are normalized to EarnWage's ISO-like selector codes.
SOURCE_PROVINCES = {
    "NL": ("NL", "ER10"), "PEI": ("PE", "ER1110"),
    "NS": ("NS", "ER12"), "NB": ("NB", "ER13"),
    "QC": ("QC", "ER24"), "ON": ("ON", "ER35"),
    "MB": ("MB", "ER46"), "SK": ("SK", "ER47"),
    "AB": ("AB", "ER48"), "BC": ("BC", "ER59"),
    "YK": ("YT", "ER6010"), "NWT": ("NT", "ER6110"),
    "NU": ("NU", "ER6210"),
}
MEASURES = {
    "low": "Low_Wage_Salaire_Minium",
    "median": "Median_Wage_Salaire_Median",
    "high": "High_Wage_Salaire_Maximal",
    "mean": "Average_Wage_Salaire_Moyen",
    "p25": "Quartile1_Wage_Salaire_Quartile1",
    "p75": "Quartile3_Wage_Salaire_Quartile3",
}
REQUIRED = {"NOC_CNP", "NOC_Title_eng", "prov", "ER_Code_Code_RE",
            "Annual_Wage_Flag_Salaire_annuel", "Reference_Period", *MEASURES.values()}
COLUMNS = ("occupation", "province", "classification", "job_title", "reference_period",
           "published_year", "measure", "unit", "value", "source", "source_url")


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS ca_province_wages(
        occupation TEXT NOT NULL, province TEXT NOT NULL,
        classification TEXT NOT NULL, job_title TEXT NOT NULL,
        reference_period TEXT NOT NULL, published_year INTEGER NOT NULL,
        measure TEXT NOT NULL, unit TEXT NOT NULL, value REAL NOT NULL,
        source TEXT NOT NULL, source_url TEXT NOT NULL,
        PRIMARY KEY(occupation,province,classification,reference_period,measure,source)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ca_province_job ON ca_province_wages(occupation,province)")


def records(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise ValueError("Unexpected Job Bank 2025 provincial CSV schema")
    by_code = {}
    for job, (noc, title) in CANADA_NOC.items():
        by_code.setdefault("NOC_" + noc, []).append((job, title))
    count = 0
    for row in reader:
        source_province = row["prov"].strip().upper()
        mapping = SOURCE_PROVINCES.get(source_province)
        if not mapping or row["ER_Code_Code_RE"].strip() != mapping[1]:
            continue
        province = mapping[0]
        code = row["NOC_CNP"].strip()
        if code not in by_code:
            continue
        period = row["Reference_Period"].strip()
        if not period or period.upper() in ("NA", "N/A"):
            continue
        flag = row["Annual_Wage_Flag_Salaire_annuel"].strip()
        if flag not in ("0", "1"):
            continue
        unit = "CAD/year" if flag == "1" else "CAD/hour"
        for job, expected in by_code[code]:
            title = row["NOC_Title_eng"].strip()
            if not title.casefold().startswith(expected.casefold()):
                raise ValueError(f"NOC title drift for {code} in {province}")
            for measure, column in MEASURES.items():
                value = number(row[column])
                if value is None:
                    continue
                count += 1
                yield (job, province, "NOC2021:" + code.removeprefix("NOC_"),
                       title, period, 2025, measure, unit, value,
                       CANADA_DATASET, CANADA_URL)
    if count == 0:
        raise ValueError("No qualifying provincial Job Bank wages")


def persist(rows):
    rows = list(rows)
    if not rows:
        raise ValueError("Refusing empty provincial import")
    if len({(r[0], r[1], r[2], r[4], r[6]) for r in rows}) != len(rows):
        raise ValueError("Ambiguous duplicate provincial observation")
    with connect() as db:
        init(db)
        db.executemany("INSERT OR REPLACE INTO ca_province_wages VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return len(rows)


def import_official():
    import httpx
    response = httpx.get(CANADA_URL, timeout=90, follow_redirects=True)
    response.raise_for_status()
    if len(response.content) > 25_000_000:
        raise ValueError("Unexpected Job Bank CSV size")
    return persist(records(response.content.decode("utf-8-sig")))


def export_snapshot(path="data/ca_province_wages.json"):
    with connect() as db:
        init(db)
        rows = db.execute("SELECT " + ",".join(COLUMNS) +
                          " FROM ca_province_wages ORDER BY occupation,province,reference_period,measure").fetchall()
    if not rows:
        raise ValueError("No provincial observations to export")
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"schema": 1, "records": [dict(zip(COLUMNS, row)) for row in rows]},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(rows)


def load_snapshot(path="data/ca_province_wages.json"):
    source = Path(path)
    if not source.exists():
        return 0
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not isinstance(payload.get("records"), list):
        raise ValueError("Invalid Canadian provincial snapshot")
    rows = []
    for record in payload["records"]:
        job, province = record["occupation"], record["province"]
        if job not in CANADA_NOC or province not in PROVINCES:
            raise ValueError("Invalid province or occupation")
        if record["classification"] != "NOC2021:" + CANADA_NOC[job][0]:
            raise ValueError("Invalid NOC classification")
        if record["measure"] not in MEASURES or record["unit"] not in ("CAD/year", "CAD/hour"):
            raise ValueError("Invalid wage metric")
        if record["published_year"] != 2025 or number(record["value"]) is None:
            raise ValueError("Invalid publication year or wage")
        rows.append(tuple(record[c] for c in COLUMNS))
    return persist(rows) if rows else 0


def wage(occupation, province):
    province = province.upper()
    if province not in PROVINCES:
        raise ValueError("Unknown Canadian province or territory")
    if occupation not in CANADA_NOC:
        return {"status": "unavailable", "country": "CA", "occupation": occupation,
                "province": province, "reason": "No approved NOC mapping"}
    with connect() as db:
        init(db)
        rows = db.execute("SELECT " + ",".join(COLUMNS) +
            """ FROM ca_province_wages WHERE occupation=? AND province=?
                ORDER BY published_year DESC,reference_period DESC,measure""",
            (occupation, province)).fetchall()
    if not rows:
        return {"status": "unavailable", "country": "CA", "occupation": occupation,
                "province": province, "province_name": PROVINCES[province],
                "reason": "No verified province-wide Job Bank observation imported"}
    records = [dict(zip(COLUMNS, row)) for row in rows]
    latest = (records[0]["published_year"], records[0]["reference_period"])
    selected = [r for r in records if (r["published_year"], r["reference_period"]) == latest]
    units = {r["unit"] for r in selected}
    if len(units) != 1:
        return {"status": "unavailable", "country": "CA", "occupation": occupation,
                "province": province, "reason": "Conflicting source units"}
    return {
        "status": "available", "country": "CA", "occupation": occupation,
        "province": province, "province_name": PROVINCES[province],
        "geography": "province", "classification": selected[0]["classification"],
        "job_title": selected[0]["job_title"], "reference_period": latest[1],
        "published_year": latest[0], "unit": selected[0]["unit"], "currency": "CAD",
        "metrics": {r["measure"]: r["value"] for r in selected},
        "source": CANADA_DATASET, "source_url": CANADA_URL,
        "note": "Provincial wage observation, not an economic-region/city wage or net income.",
    }


def coverage():
    with connect() as db:
        init(db)
        count, pairs, provinces = db.execute(
            "SELECT COUNT(*),COUNT(DISTINCT occupation || ':' || province),COUNT(DISTINCT province) FROM ca_province_wages"
        ).fetchone()
    return {"observations": count, "occupation_province_pairs": pairs,
            "provinces_or_territories": provinces, "source_url": CANADA_URL}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-official", action="store_true")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    if args.import_official:
        print(json.dumps({"imported": import_official(), "source": CANADA_URL}))
    if args.export:
        print(json.dumps({"exported": export_snapshot()}))
    if not args.import_official and not args.export:
        parser.error("Choose --import-official and/or --export")


def bulk_rows(stream, geographies):
    """Strict streaming release reader shared with offline Phase 4 bulk staging.

    Geographic identifiers/names must match the reviewed official release
    registry; province totals and economic regions remain distinct.
    """
    import re
    from decimal import Decimal, InvalidOperation
    reader=csv.DictReader(stream)
    required=REQUIRED | {'ER_Name','Data_Source_E','Revision_Date_Date_revision'}
    if not required <= set(reader.fieldnames or []):
        raise ValueError('Unexpected Job Bank bulk layout')
    seen=set()
    for row in reader:
        if None in row or any(v is None for v in row.values()):raise ValueError('Malformed CSV row')
        code=row['NOC_CNP'].strip();area=row['ER_Code_Code_RE'].strip();prov=row['prov'].strip()
        if not re.fullmatch(r'NOC_\d{5}',code) or not row['NOC_Title_eng'].strip():raise ValueError('Invalid NOC2021 code/title')
        if geographies.get(area)!={'province':prov,'name':row['ER_Name']}:
            raise ValueError('Unverified geography identifier or name')
        if prov=='NAT':
            if area!='ER00':raise ValueError('Invalid national geography')
            geo='national'
        elif prov in SOURCE_PROVINCES:
            normalized,total=SOURCE_PROVINCES[prov]
            geo='CA:province:'+normalized if area==total else 'CA:economic_region:'+area
        else:raise ValueError('Unverified province')
        flag=row['Annual_Wage_Flag_Salaire_annuel'].strip()
        if flag not in ('0','1'):raise ValueError('Unverified wage unit')
        period=row['Reference_Period'].strip()
        if period!='NA' and not re.fullmatch(r'20\d{2}(?:-20\d{2})?',period):raise ValueError('Unverified period')
        identity=(code,area,period,flag)
        if identity in seen:raise ValueError('Duplicate Job Bank scope')
        seen.add(identity)
        values={}
        for measure,column in MEASURES.items():
            raw=row[column].strip()
            if not raw:values[measure]=None;continue
            try:value=Decimal(raw)
            except InvalidOperation:raise ValueError('Unknown salary token') from None
            if not value.is_finite() or value<0:raise ValueError('Invalid salary')
            if period=='NA':raise ValueError('Salary without reference period')
            values[measure]=str(value)
        yield row,geo,'CAD/year' if flag=='1' else 'CAD/hour',values

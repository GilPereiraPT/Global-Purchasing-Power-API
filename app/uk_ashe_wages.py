"""UK ONS ASHE 2025 occupation-specific annual gross pay (SOC 2020).

Source: ASHE Table 14.7a (annual gross pay) + 14.7b (CV), corrected
2025 provisional release. Only manually approved one-to-one EarnWage ↔
SOC 2020 unit-group mappings are admitted. Broad titles remain unavailable.
"""
import argparse
import io
import json
import math
import re
import zipfile
from pathlib import Path

import httpx
from openpyxl import load_workbook

from app.store import connect

SOURCE = "Office for National Statistics (ONS), Annual Survey of Hours and Earnings"
DATASET = "ASHE Table 14, 2025 provisional (corrected 19 December 2025)"
SOURCE_PAGE = ("https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/"
               "earningsandworkinghours/datasets/occupation4digitsoc2010ashetable14/"
               "2025provisional")
SOURCE_ZIP = ("https://www.ons.gov.uk/file?uri=%2Femploymentandlabourmarket%2Fpeopleinwork%2F"
              "earningsandworkinghours%2Fdatasets%2Foccupation4digitsoc2010ashetable14%2F"
              "2025provisional%2Fashetable142025provisional.zip")
LICENCE = "Open Government Licence v3.0"
YEAR = 2025
MAX_ZIP = 30 * 1024 * 1024
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "uk_ashe_wages.json"

# Exact unit-group matches only. Do not fill broad EarnWage titles by aggregation.
SOC2020 = {
    "accountant": ("2421", "Chartered and certified accountants"),
    "financial_analyst": ("2422", "Finance and investment analysts and advisers"),
    "pharmacist": ("2251", "Pharmacists"),
    "physiotherapist": ("2221", "Physiotherapists"),
    "preschool_teacher": ("2315", "Nursery education teaching professionals"),
    "software_developer": ("2134", "Programmers and software development professionals"),
    "civil_engineer": ("2121", "Civil engineers"),
    "mechanical_engineer": ("2122", "Mechanical engineers"),
    "architect": ("2451", "Architects"),
    "receptionist": ("4216", "Receptionists"),
    "sales_assistant": ("7111", "Sales and retail assistants"),
    "truck_driver": ("8211", "Large goods vehicle drivers"),
    "bus_driver": ("8212", "Bus and coach drivers"),
    "electrician": ("5241", "Electricians and electrical fitters"),
    "plumber": ("5315", "Plumbers and heating and ventilating installers and repairers"),
    "cook": ("5435", "Cooks"),
    "waiter": ("9264", "Waiters and waitresses"),
    "cleaner": ("9223", "Cleaners and domestics"),
    "security_guard": ("9231", "Security guards and related occupations"),
    "dentist": ("2253", "Dental practitioners"),
    "healthcare_assistant": ("6131", "Nursing auxiliaries and assistants"),
    "data_analyst": ("3544", "Data analysts"),
    "cybersecurity_specialist": ("2135", "Cyber security professionals"),
    "secondary_teacher": ("2313", "Secondary education teaching professionals"),
    "warehouse_operator": ("9252", "Warehouse operatives"),
    "welder": ("5213", "Welding trades"),
    "automotive_mechanic": ("5231", "Vehicle technicians, mechanics and electricians"),
}
CODE_TO_JOB = {code: (job, title) for job, (code, title) in SOC2020.items()}
if len(CODE_TO_JOB) != len(SOC2020):
    raise RuntimeError("Repeated UK SOC mapping")

COLUMNS = (
    "country","occupation","geography","classification","job_title",
    "reference_period","published_year","release_status","currency",
    "measure","unit","value","cv_percent","quality","source","source_url",
)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value=float(value)
    return value if math.isfinite(value) and value > 0 else None


def _find_member(archive, table):
    candidates=[x for x in archive.infolist()
                if not x.is_dir() and x.filename.lower().endswith(".xlsx")
                and table.lower() in x.filename.lower()]
    if len(candidates) != 1:
        raise ValueError("Expected one official " + table + " workbook")
    return candidates[0]


def _sheet_rows(payload, sheet="All"):
    wb=load_workbook(io.BytesIO(payload),read_only=True,data_only=True)
    try:
        if sheet not in wb.sheetnames:
            raise ValueError("Missing ONS sheet: "+sheet)
        ws=wb[sheet]
        header=[ws.cell(5,c).value for c in range(1,8)]
        if header != ["Description","Code","(thousand)","Median","change","Mean","change"]:
            raise ValueError("Unexpected ONS Table 14.7 header")
        rows={}
        for r in range(6,ws.max_row+1):
            code=str(ws.cell(r,2).value or "").strip()
            if re.fullmatch(r"[0-9]{4}",code):
                rows[code]={
                    "title":str(ws.cell(r,1).value or "").strip(),
                    "median":ws.cell(r,4).value,
                    "mean":ws.cell(r,6).value,
                }
        if len(rows) < 300:
            raise ValueError("Too few SOC 2020 unit groups in ONS workbook")
        return rows
    finally:
        wb.close()


def build_snapshot(zip_path):
    """Derive a public aggregate snapshot; no microdata are involved."""
    raw=Path(zip_path).read_bytes()
    if not raw.startswith(b"PK") or len(raw) > MAX_ZIP:
        raise ValueError("Invalid or oversized ONS ASHE ZIP")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        z.testzip()
        pay=_sheet_rows(z.read(_find_member(z,"Table 14.7a")))
        cv=_sheet_rows(z.read(_find_member(z,"Table 14.7b")))
    records=[]
    rejected=[]
    for code,(job,expected) in CODE_TO_JOB.items():
        p=pay.get(code)
        q=cv.get(code)
        if not p or not q or p["title"] != expected or q["title"] != expected:
            rejected.append({"occupation":job,"soc2020":code,"reason":"missing_or_title_mismatch"})
            continue
        for measure in ("median","mean"):
            value=_number(p[measure])
            cv_value=_number(q[measure])
            # Public ASHE uses x / punctuation for suppression. Never infer it.
            if value is None or cv_value is None or cv_value > 20:
                rejected.append({"occupation":job,"soc2020":code,
                                 "measure":measure,"reason":"suppressed_or_cv_over_20"})
                continue
            quality=("precise" if cv_value <= 5 else
                     "reasonably_precise" if cv_value <= 10 else "acceptable")
            records.append(dict(zip(COLUMNS,(
                "GB",job,"national","SOC2020:"+code,expected,
                str(YEAR),YEAR,"provisional","GBP",measure,"GBP/year",
                value,cv_value,quality,SOURCE,SOURCE_PAGE,
            ))))
    if not records:
        raise ValueError("No validated UK ASHE exact-occupation records")
    return {
        "schema":1,"source":SOURCE,"dataset":DATASET,"source_url":SOURCE_PAGE,
        "source_download":SOURCE_ZIP,"licence":LICENCE,
        "reference_period":str(YEAR),"release_status":"provisional",
        "preferred_measure":"median",
        "mapping_count":len(SOC2020),"records":records,"rejected":rejected,
        "note":"Only direct EarnWage-to-SOC2020 unit-group matches. Broad occupations are intentionally absent.",
    }


def fetch_zip():
    timeout=httpx.Timeout(connect=20,read=120,write=20,pool=20)
    with httpx.Client(timeout=timeout,follow_redirects=True) as client:
        response=client.get(SOURCE_ZIP)
        response.raise_for_status()
    if len(response.content) > MAX_ZIP:
        raise ValueError("ONS ZIP exceeds configured size limit")
    return response.content


def export_snapshot(path=DEFAULT, source_zip=None):
    raw=fetch_zip() if source_zip is None else Path(source_zip).read_bytes()
    temp=Path(str(path)+".source.tmp")
    try:
        temp.write_bytes(raw)
        obj=build_snapshot(temp)
    finally:
        temp.unlink(missing_ok=True)
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return obj


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS uk_ashe_wages (
        country TEXT NOT NULL, occupation TEXT NOT NULL, geography TEXT NOT NULL,
        classification TEXT NOT NULL, job_title TEXT NOT NULL,
        reference_period TEXT NOT NULL, published_year INTEGER NOT NULL,
        release_status TEXT NOT NULL, currency TEXT NOT NULL, measure TEXT NOT NULL,
        unit TEXT NOT NULL, value REAL NOT NULL, cv_percent REAL NOT NULL,
        quality TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL,
        PRIMARY KEY(country,occupation,reference_period,measure)
    )""")


def load_snapshot(path=DEFAULT):
    path=Path(path)
    if not path.exists():
        return 0
    obj=json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != 1 or obj.get("preferred_measure") != "median":
        raise ValueError("Invalid UK ASHE snapshot schema")
    validated=[]
    for r in obj.get("records",[]):
        mapping=SOC2020.get(r.get("occupation"))
        expected=(r.get("classification") or "").removeprefix("SOC2020:")
        if (r.get("country")!="GB" or mapping is None or mapping[0] != expected or
            mapping[1] != r.get("job_title") or r.get("reference_period")!="2025" or
            r.get("release_status")!="provisional" or r.get("currency")!="GBP" or
            r.get("unit")!="GBP/year" or r.get("measure") not in ("median","mean") or
            _number(r.get("value")) is None or _number(r.get("cv_percent")) is None or
            r["cv_percent"] > 20 or r.get("source") != SOURCE or
            r.get("source_url") != SOURCE_PAGE):
            raise ValueError("Unverified UK ASHE snapshot row")
        validated.append(tuple(r[c] for c in COLUMNS))
    if not validated:
        raise ValueError("Empty UK ASHE snapshot")
    with connect() as db:
        init(db)
        db.executemany("INSERT OR REPLACE INTO uk_ashe_wages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       validated)
        db.commit()
    return len(validated)


def observed_coverage():
    with connect() as db:
        init(db)
        rows=db.execute("""SELECT occupation,COUNT(*),MAX(reference_period)
                           FROM uk_ashe_wages GROUP BY occupation""").fetchall()
    return {job:(count,period) for job,count,period in rows}


def wages(country, occupation):
    if country != "GB":
        return {"status":"unavailable","country":country,"occupation":occupation,
                "reason":"UK ASHE only applies to GB/United Kingdom"}
    with connect() as db:
        init(db)
        rows=db.execute("""SELECT geography,classification,job_title,reference_period,
            published_year,release_status,currency,measure,unit,value,cv_percent,
            quality,source,source_url FROM uk_ashe_wages
            WHERE country='GB' AND occupation=? ORDER BY measure""",
            (occupation,)).fetchall()
    if not rows:
        reason=("EarnWage title does not have an approved one-to-one SOC 2020 unit-group mapping"
                if occupation not in SOC2020 else "No unsuppressed ASHE estimate with CV <= 20%")
        return {"status":"unavailable","country":"GB","occupation":occupation,
                "geography":"national","reason":reason}
    keys=("geography","classification","job_title","reference_period","published_year",
          "release_status","currency","measure","unit","value","cv_percent","quality",
          "source","source_url")
    return {
        "status":"available","country":"GB","occupation":occupation,
        "geography":"national","reference_period":rows[0][3],
        "published_year":rows[0][4],"release_status":rows[0][5],
        "preferred_measure":"median",
        "observations":[dict(zip(keys,row)) for row in rows],
        "precision":"exact_occupation_soc2020",
        "note":"ONS ASHE annual gross employee pay; median is ONS's preferred typical-pay measure. Provisional 2025 data may be revised.",
    }


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-zip",type=Path)
    parser.add_argument("--export",type=Path,default=DEFAULT)
    args=parser.parse_args(argv)
    obj=export_snapshot(args.export,args.source_zip)
    print(json.dumps({"export":str(args.export),"records":len(obj["records"]),
                      "mapped_occupations":len({r["occupation"] for r in obj["records"]}),
                      "rejected":len(obj["rejected"])},ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

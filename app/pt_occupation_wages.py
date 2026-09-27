"""Safe source-backed PT salary import: INE/GEP 0010385, validated CPP-2010 categories.

CLI: inspect the official JSON; export ONLY manually approved exact 4-digit
occupation codes to a snapshot. No network on production request paths.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

from app.catalog import OCCUPATIONS
from app.store import connect

INDICATOR = "0010385"
URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010385&lang=PT"
META_URL = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0010385&lang=PT"
SOURCE = "INE/GEP Quadros de Pessoal: ganho médio mensal por profissão CPP"
LICENCE = "CC BY 4.0"
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "pt_occupation_wages.json"
JOBS = {item["id"] for item in OCCUPATIONS}
FIELDS = ("country","occupation","period","classification","job_title",
          "geography","measure","salary_concept","unit","currency","value",
          "source","source_url","licence")
MAX_BYTES = 30 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 18.0
READ_TIMEOUT_SECONDS = 75.0
NETWORK_ATTEMPTS = 3
RETRY_PAUSES_SECONDS = (3, 8)


def fold(s):
    text = unicodedata.normalize("NFKD", str(s))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).casefold().split())


def number(raw):
    if isinstance(raw, bool) or raw is None:
        return None
    s = str(raw).strip().replace(" ","").replace("\u00a0","")
    if "," in s and "." in s:
        return None
    s = s.replace(",",".")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,4})?",s):
        return None
    try:
        n = Decimal(s)
    except InvalidOperation:
        return None
    return float(n) if n.is_finite() and 0 < n < 1000000 else None


def flatten(payload):
    if not isinstance(payload,list) or len(payload)!=1 or not isinstance(payload[0],dict):
        raise ValueError("Expected one official INE indicator object")
    obj=payload[0]
    if str(obj.get("IndicadorCod"))!=INDICATOR or "ganho medio mensal" not in fold(obj.get("IndicadorDsg","")):
        raise ValueError("Incorrect official salary indicator/measure")
    data=obj.get("Dados")
    if not isinstance(data,dict) or not data:
        raise ValueError("Missing INE Dados by year")
    out=[]
    for year,items in data.items():
        if not re.fullmatch(r"20[0-9]{2}",str(year)) or not isinstance(items,list):
            raise ValueError("Unsupported period or INE schema")
        for item in items:
            if not isinstance(item,dict) or "geocod" not in item or "geodsg" not in item:
                raise ValueError("INE row is missing its geography")
            out.append((str(year),item))
    if not out:
        raise ValueError("Official indicator contains no rows")
    return obj,out


def inspect(payload):
    obj,rows=flatten(payload)
    categories={}
    for _,row in rows:
        for key,value in row.items():
            if re.fullmatch(r"dim_[2-9]",key):
                categories.setdefault(key,set()).add((str(value),str(row.get(key+"_t",""))))
    places=sorted({(str(r["geocod"]),str(r["geodsg"])) for _,r in rows})
    return {"indicator":INDICATOR,"title":obj["IndicadorDsg"],
            "years":sorted({year for year,_ in rows}),"rows":len(rows),
            "geographies":[{"code":c,"label":label} for c,label in places[:100]],
            "geography_truncated":len(places)>100,
            "dimensions":{k:[{"code":c,"label":label} for c,label in sorted(v)[:300]]
                          for k,v in sorted(categories.items())},
            "note":"Inspect the source dimension, geography and exact CPP labels before mapping."}


def check_mapping(mapping):
    if not isinstance(mapping,dict) or mapping.get("indicator")!=INDICATOR:
        raise ValueError("Explicit INE indicator approval required")
    dim=mapping.get("occupation_dimension")
    geo=mapping.get("geography")
    if not isinstance(dim,str) or not re.fullmatch(r"dim_[2-9]",dim):
        raise ValueError("Select the actual INE occupation dimension")
    if not isinstance(geo,dict) or not str(geo.get("code","")) or fold(geo.get("label",""))!="portugal":
        raise ValueError("Only an explicitly verified Portugal national geography is accepted")
    entries=mapping.get("occupations")
    if not isinstance(entries,list) or not entries:
        raise ValueError("Empty or missing approved occupation mappings")
    jobs,codes=set(),set()
    for item in entries:
        if not isinstance(item,dict):
            raise ValueError("Invalid mapping entry")
        job,code,label=item.get("occupation"),item.get("cpp_code"),item.get("cpp_label")
        if (job not in JOBS or not isinstance(code,str) or
                not re.fullmatch(r"[0-9]{4}",code) or
                not isinstance(label,str) or not label.strip()):
            raise ValueError("Only known occupations with an explicit 4-digit CPP code and label")
        if job in jobs or code in codes:
            raise ValueError("Duplicate or ambiguous profession mapping")
        jobs.add(job);codes.add(code)
    return mapping


def build_records(payload,mapping):
    check_mapping(mapping)
    _,rows=flatten(payload)
    dim=mapping["occupation_dimension"]
    geo=mapping["geography"]
    approved={x["cpp_code"]:x for x in mapping["occupations"]}
    out,seen,matched=[],set(),set()
    for year,row in rows:
        if str(row["geocod"])!=str(geo["code"]) or fold(row["geodsg"])!=fold(geo["label"]):
            continue
        code=str(row.get(dim,""))
        if code not in approved:
            continue
        item=approved[code]
        if not isinstance(row.get(dim+"_t"),str) or fold(row[dim+"_t"])!=fold(item["cpp_label"]):
            raise ValueError("INE CPP label drift: "+code)
        matched.add(code)
        value=number(row.get("valor"))
        if value is None:  # missing/confidential data are NOT zero
            continue
        key=(item["occupation"],year)
        if key in seen:
            raise ValueError("Duplicate source observations: "+repr(key))
        seen.add(key)
        out.append({"country":"PT","occupation":item["occupation"],"period":year,
                    "classification":"CPP2010:"+code,"job_title":row[dim+"_t"],
                    "geography":"national","measure":"mean","salary_concept":"monthly_gain",
                    "unit":"EUR/month","currency":"EUR","value":value,
                    "source":SOURCE,"source_url":URL,"licence":LICENCE})
    absent=set(approved)-matched
    if absent:
        raise ValueError("CPP categories absent from payload: "+",".join(sorted(absent)))
    if not out:
        raise ValueError("No eligible occupation salary data; refusing empty snapshot")
    return sorted(out,key=lambda r:(r["occupation"],r["period"]))


def export(payload,mapping,dest):
    records=build_records(payload,mapping)
    p=Path(dest)
    if p.exists():
        raise FileExistsError("No implicit overwrite of validated snapshot")
    p.parent.mkdir(parents=True,exist_ok=True)
    obj={"schema":1,"indicator":INDICATOR,"source":SOURCE,"source_url":URL,
         "metadata_url":META_URL,"licence":LICENCE,"records":records}
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"exported":len(records),"occupations":sorted({r["occupation"] for r in records})}


def validate_snapshot(obj):
    if (not isinstance(obj,dict) or obj.get("schema")!=1 or
            obj.get("indicator")!=INDICATOR or obj.get("source")!=SOURCE or
            obj.get("source_url")!=URL or obj.get("licence")!=LICENCE or
            not isinstance(obj.get("records"),list)):
        raise ValueError("Unrecognised INE/GEP salary snapshot")
    output,seen=[],set()
    for r in obj["records"]:
        if not isinstance(r,dict) or set(r)!=set(FIELDS):
            raise ValueError("Unrecognised PT salary row structure")
        if (r["country"]!="PT" or r["occupation"] not in JOBS or
                not isinstance(r["classification"],str) or
                not re.fullmatch(r"CPP2010:[0-9]{4}",r["classification"]) or
                not re.fullmatch(r"20[0-9]{2}",str(r["period"])) or
                r["geography"]!="national" or r["measure"]!="mean" or
                r["salary_concept"]!="monthly_gain" or r["unit"]!="EUR/month" or
                r["currency"]!="EUR" or r["source"]!=SOURCE or
                r["source_url"]!=URL or r["licence"]!=LICENCE or number(r["value"]) is None):
            raise ValueError("Invalid Portuguese wage source, unit, year or occupation")
        key=(r["occupation"],r["period"])
        if key in seen:
            raise ValueError("Several CPP codes for the same profession/year")
        seen.add(key)
        output.append(tuple(r[k] for k in FIELDS))
    if not output:
        raise ValueError("Refusing empty PT wage snapshot")
    return output


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS pt_occupation_wages (
       country TEXT NOT NULL, occupation TEXT NOT NULL, period TEXT NOT NULL,
       classification TEXT NOT NULL, job_title TEXT NOT NULL,
       geography TEXT NOT NULL, measure TEXT NOT NULL, salary_concept TEXT NOT NULL,
       unit TEXT NOT NULL, currency TEXT NOT NULL, value REAL NOT NULL,
       source TEXT NOT NULL, source_url TEXT NOT NULL, licence TEXT NOT NULL,
       PRIMARY KEY(country,occupation,period,classification,source))""")


def load_snapshot(path=DEFAULT):
    p=Path(path)
    if not p.is_file():
        return 0
    records=validate_snapshot(json.loads(p.read_text(encoding="utf-8")))
    with connect() as db:
        init(db)
        db.executemany("INSERT OR REPLACE INTO pt_occupation_wages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",records)
        db.commit()
    return len(records)


def observed_coverage():
    with connect() as db:
        init(db)
        rows=db.execute("""SELECT country,occupation,COUNT(*),MAX(period)
            FROM pt_occupation_wages GROUP BY country,occupation""").fetchall()
    return {(country,job):(count,year) for country,job,count,year in rows}


def wages(country,occupation):
    if country!="PT" or occupation not in JOBS:
        return {"status":"unavailable","country":country,"occupation":occupation}
    with connect() as db:
        init(db)
        rows=db.execute("""SELECT period,classification,job_title,value,source,
            source_url,licence FROM pt_occupation_wages
            WHERE country=? AND occupation=? ORDER BY period DESC""",
            ("PT",occupation)).fetchall()
    if not rows:
        return {"status":"unavailable","country":"PT","occupation":occupation,
                "reason":"No verified exact CPP occupation salary imported"}
    latest=[r for r in rows if r[0]==rows[0][0]]
    if len(latest)!=1:
        return {"status":"ambiguous","country":"PT","occupation":occupation}
    year,cpp,title,value,source,url,licence=latest[0]
    return {"status":"available","country":"PT","occupation":occupation,
            "period":year,"reference_period":year,"value":value,"currency":"EUR",
            "unit":"monthly gross earnings (gain, as reported by INE/GEP)",
            "measure":"mean","salary_concept":"monthly_gain","geography":"national",
            "classification":cpp,"job_title":title,"precision":"occupation_specific_cpp2010",
            "source":source,"source_url":url,"licence":licence,
            "note":"INE/GEP mean monthly gain for the Quadros de Pessoal employee universe; not a public pay scale or a verified 14-pay annual salary."}


def fetch():
    """Attempt only bounded retries for transient INE network/server faults.

    HTTP 4xx (except 429), invalid JSON and unexpected schema MUST NOT be
    retried or treated as salary data. Nothing is stored on failed inspection.
    """
    timeout=httpx.Timeout(connect=CONNECT_TIMEOUT_SECONDS,
                          read=READ_TIMEOUT_SECONDS,write=20.0,pool=20.0)
    for attempt in range(1,NETWORK_ATTEMPTS+1):
        try:
            with httpx.Client(timeout=timeout,follow_redirects=True,
                              trust_env=True) as client:
                with client.stream("GET",URL) as response:
                    response.raise_for_status()
                    pieces,size=[],0
                    for part in response.iter_bytes():
                        size+=len(part)
                        if size>MAX_BYTES:
                            raise ValueError("Official INE payload exceeds size limit")
                        pieces.append(part)
            return json.loads(b"".join(pieces).decode("utf-8-sig"))
        except (httpx.ConnectTimeout,httpx.ReadTimeout,httpx.ConnectError,
                httpx.ReadError,httpx.RemoteProtocolError) as exc:
            reason=type(exc).__name__
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (429,500,502,503,504):
                raise
            reason="HTTP "+str(exc.response.status_code)
        if attempt==NETWORK_ATTEMPTS:
            raise RuntimeError(
                "INE official source unreachable after 3 bounded attempts ("
                +reason+"). No data were imported. Download its JSON manually "
                "and run --source FILE --inspect; see PT_WAGE_IMPORT_RUNBOOK.md."
            ) from None
        pause=RETRY_PAUSES_SECONDS[attempt-1]
        print("INE request attempt "+str(attempt)+"/"+
              str(NETWORK_ATTEMPTS)+" failed ("+reason+
              "); retrying after "+str(pause)+"s.",file=sys.stderr,flush=True)
        time.sleep(pause)
    raise AssertionError("Unreachable retry state")


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source",type=Path,help="Previously downloaded official JSON")
    source.add_argument("--fetch",action="store_true",help="Download INE JSON once")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect",action="store_true",help="List source codes only")
    mode.add_argument("--export",type=Path,help="New vetted JSON snapshot")
    parser.add_argument("--mapping",type=Path,help="Manually approved CPP codes/labels")
    args=parser.parse_args(argv)
    try:
        payload=fetch() if args.fetch else json.loads(args.source.read_text(encoding="utf-8-sig"))
    except RuntimeError as exc:
        print("INE inspection not completed: "+str(exc),file=sys.stderr)
        return 2
    if args.inspect:
        print(json.dumps(inspect(payload),ensure_ascii=False,indent=2))
        return 0
    if args.mapping is None:
        parser.error("--mapping is required for export")
    mapping=json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    print(json.dumps(export(payload,mapping,args.export),ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

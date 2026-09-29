"""Swiss FSO ESS 2024 CH-ISCO-19 sub-major-group wage context.

The official table publishes CH-ISCO-19 only at 1-2 digits. These observations
are deliberately GROUP CONTEXT, never relabelled as exact occupation wages.
"""
import json
from pathlib import Path

SOURCE="Swiss Federal Statistical Office (FSO), Earnings Structure Survey (ESS)"
TABLE="px-x-0304010000_205"
SOURCE_URL="https://www.pxweb.bfs.admin.ch/pxweb/en/px-x-0304010000_205/-/px-x-0304010000_205.px/"
DEFAULT=Path(__file__).resolve().parent.parent/"data"/"ch_bfs_wages.json"

# CH-ISCO-19 uses ISCO-08 levels 1-4; these are curated 2-digit mappings for
# EarnWage interface occupations. Generic titles remain explicitly cautioned.
SUBMAJOR={
 "accountant":"24","auditor":"24","financial_analyst":"24",
 "doctor":"22","nurse":"22","pharmacist":"22","psychologist":"26",
 "physiotherapist":"22","teacher":"23","preschool_teacher":"23",
 "software_developer":"25","it_technician":"35","civil_engineer":"21",
 "mechanical_engineer":"21","architect":"21","administrative_assistant":"41",
 "manager":"12","receptionist":"42","sales_assistant":"52",
 "supermarket_worker":"52","truck_driver":"83","bus_driver":"83",
 "electrician":"74","plumber":"71","construction_worker":"93","cook":"51",
 "waiter":"51","cleaner":"91","security_guard":"54","lawyer":"26",
 "dentist":"22","healthcare_assistant":"53","data_analyst":"25",
 "cybersecurity_specialist":"25","secondary_teacher":"23",
 "warehouse_operator":"93","industrial_operator":"81","welder":"72",
 "automotive_mechanic":"72","agricultural_worker":"92"
}
CAUTION={
 "manager":"Generic manager title; CH-ISCO sub-major group depends on managerial function.",
 "teacher":"Teaching level can change the detailed occupation; this is group context.",
 "supermarket_worker":"Checkout, sales, warehouse and management roles can differ.",
 "construction_worker":"Skilled trades and elementary construction work differ.",
 "warehouse_operator":"Warehouse clerks, drivers and manual handlers can differ.",
 "industrial_operator":"Machine type and duties determine the detailed occupation.",
 "agricultural_worker":"Skilled agriculture and elementary farm work differ.",
 "data_analyst":"Data roles may fall in different detailed occupations.",
 "it_technician":"IT support and software roles belong to different sub-major groups."
}

def load_snapshot(path=DEFAULT):
    p=Path(path)
    if not p.exists(): return []
    data=json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or data.get("table")!=TABLE:
        raise ValueError("Unsupported Swiss FSO wage snapshot")
    return data.get("observations",[])

def context(occupation,path=DEFAULT):
    group=SUBMAJOR.get(occupation)
    if not group:
        return {"status":"unavailable","country":"CH","occupation":occupation,
                "precision":"ch_isco19_submajor_group"}
    rows=[r for r in load_snapshot(path) if r.get("ch_isco19_submajor_group")==group
          and r.get("geography")=="Switzerland" and r.get("age")=="total"
          and r.get("sex")=="total"]
    if not rows:
        return {"status":"unavailable","country":"CH","occupation":occupation,
                "ch_isco19_submajor_group":group,"precision":"ch_isco19_submajor_group",
                "source":SOURCE,"source_url":SOURCE_URL,
                "reason":"Official Swiss group snapshot not imported yet"}
    period=max(str(r["period"]) for r in rows)
    selected=[r for r in rows if str(r["period"])==period]
    values={r["percentile"]:r["value"] for r in selected if r.get("value") is not None}
    return {"status":"available","country":"CH","occupation":occupation,"period":period,
            "ch_isco19_submajor_group":group,"precision":"ch_isco19_submajor_group",
            "geography":"national","currency":"CHF",
            "unit":"standardised gross monthly wage","values":values,
            "preferred_measure":"median","value":values.get("median"),
            "source":SOURCE,"dataset":TABLE,"source_url":SOURCE_URL,
            "mapping_caution":CAUTION.get(occupation),
            "note":"Official CH-ISCO-19 2-digit group context, not an individual occupation wage. Full-time equivalent: 4 1/3 weeks at 40 hours; includes 1/12 of 13th salary and annual special payments."}

def observed_coverage(path=DEFAULT):
    rows=load_snapshot(path)
    groups={r.get("ch_isco19_submajor_group") for r in rows
            if r.get("geography")=="Switzerland" and r.get("age")=="total"
            and r.get("sex")=="total" and r.get("percentile")=="median"}
    return {job for job,group in SUBMAJOR.items() if group in groups}

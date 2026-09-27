"""Official INE Spain EAES table 28186: broad CNO-11 occupation groups only.

Independent context series; NEVER used by wage_for, annual_presentation,
exact_history, occupation-specific salary matrix or ISCO-08 group labels.
Reads a versioned official JSON aggregate snapshot; no upstream network.
"""
import json
import math
import re
from functools import lru_cache
from pathlib import Path

SOURCE = "Instituto Nacional de Estadística (INE), Encuesta Anual de Estructura Salarial"
SOURCE_URL = "https://www.ine.es/jaxiT3/Tabla.htm?t=28186"
OPEN_DATA_LICENSE = "CC BY 4.0"
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "es_ine_eaes_28186.json"
GROUPS = ("TOTAL", *"ABCDEFGHIJKLMNOPQ")
SEX_LABELS = {"both": "Ambos sexos", "women": "Mujeres", "men": "Hombres"}
YEARS = set(range(2008, 2025))
LOW_SAMPLE_NOTE = "100 y 500"
MIN_SAMPLE_NOTE = "inferior a 100"


def _metadata(entry, variable):
    matches = [m for m in entry["MetaData"] if m.get("T3_Variable") == variable]
    if len(matches) != 1:
        raise ValueError("Unexpected INE source metadata for " + variable)
    return matches[0]


@lru_cache(maxsize=4)
def _source(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list) or len(raw) != 54:
        raise ValueError("Expected the full 54-series official INE EAES table 28186")
    output,seen = {},set()
    for entry in raw:
        if entry.get("T3_Unidad") != "Euros" or not re.fullmatch(r"EAES[0-9]+", entry.get("COD", "")):
            raise ValueError("Incorrect source series or monetary unit")
        occupation = entry["MetaData"][0]
        if occupation.get("T3_Variable") not in ("OCUPACIONES", "TOTALES OCUPACIONES"):
            raise ValueError("Unexpected occupation classification")
        group = occupation.get("Codigo") or "TOTAL"
        sex = next((s for s, label in SEX_LABELS.items()
                    if _metadata(entry, "Sexo").get("Nombre") == label), None)
        geography = _metadata(entry, "Total Nacional")
        pay = _metadata(entry, "Conceptos salariales/laborales")
        if (group not in GROUPS or sex is None or
                geography.get("Codigo") != "00" or
                geography.get("Nombre") != "Total Nacional" or
                pay.get("Nombre") != "Salario medio bruto"):
            raise ValueError("Unverified CNO, geography, sex or earnings concept")
        if group == "TOTAL" and occupation.get("Nombre") != "Todas las ocupaciones":
            raise ValueError("Unexpected overall-total label")
        key = (group, sex)
        if key in seen:
            raise ValueError("Repeated group × sex in official source")
        seen.add(key)
        observations,years = [],set()
        for record in entry["Data"]:
            year = record.get("Anyo")
            if (type(year) is not int or year not in YEARS or year in years or
                    record.get("T3_Periodo") != "A" or
                    record.get("T3_TipoDato") != "Definitivo"):
                raise ValueError("Invalid/repeated official year or annual period")
            years.add(year)
            original = record.get("Valor")
            notes = record.get("Notas") or []
            low_sample = (type(original) in (int,float) and original < 0 and
                          any(LOW_SAMPLE_NOTE in note.get("texto","") for note in notes))
            suppressed = original is None and any(
                MIN_SAMPLE_NOTE in note.get("texto","") for note in notes)
            if original is None:
                value=None
                status="suppressed" if suppressed else "unavailable"
                quality="sample_below_100" if suppressed else "not_published"
            elif (type(original) in (int,float) and math.isfinite(original) and
                  original != 0 and abs(original) < 1_000_000 and
                  (original > 0 or low_sample)):
                value=abs(original)
                status="available"
                quality="sample_100_to_500_high_variability" if low_sample else "published"
            else:
                raise ValueError("Invalid source wage or unexplained negative flag")
            observations.append({
                "year":year, "value":value, "status":status,
                "sample_quality":quality, "currency":"EUR", "unit":"EUR/year",
                "source_series":entry["COD"]
            })
        if years != YEARS:
            raise ValueError("Incomplete expected 2008–2024 source years")
        output[key] = {"group":group, "group_label":occupation["Nombre"],
                       "sex":sex, "sex_label":SEX_LABELS[sex],
                       "observations":sorted(observations,key=lambda x:x["year"],reverse=True)}
    if len(output) != 54:
        raise ValueError("Missing CNO group / sex in source")
    return output


def catalogue(path=DEFAULT):
    if not Path(path).is_file():
        return {"status":"not_imported","country":"ES","source":SOURCE,
                "source_url":SOURCE_URL,"precision":"cno11_major_group"}
    data=_source(str(path))
    groups=[]
    for code in GROUPS:
        row=data[(code,"both")]
        latest=row["observations"][0]
        groups.append({"code":code,"label":row["group_label"],
                       "latest_year":latest["year"],
                       "latest_value":latest["value"],"latest_status":latest["status"],
                       "latest_quality":latest["sample_quality"]})
    observations=[v for series in data.values() for v in series["observations"]]
    return {
        "status":"available","country":"ES","source":SOURCE,
        "source_url":SOURCE_URL,"source_table":"28186",
        "licence":OPEN_DATA_LICENSE,
        "precision":"cno11_major_group", "period":"2008-2024",
        "currency":"EUR","unit":"EUR/year","measure":"mean",
        "salary_concept":"gross_annual_wage","geography":"national",
        "group_count":17,"plus_total":True,"sex_count":3,
        "published_observations":sum(x["status"]=="available" for x in observations),
        "suppressed_or_missing":sum(x["status"]!="available" for x in observations),
        "high_variability_observations":sum(
            x["sample_quality"]=="sample_100_to_500_high_variability" for x in observations),
        "groups":groups,
        "warning":"NOT individual occupation salaries. A CNO-11 major group is not a doctor/nurse/psychologist wage."
    }


def group_history(group, sex="both", start_year=2008, end_year=2024, path=DEFAULT):
    group=group.upper()
    if (group not in GROUPS or sex not in SEX_LABELS or
            type(start_year) is not int or type(end_year) is not int or
            start_year < 2008 or end_year > 2024 or start_year > end_year):
        raise ValueError("Invalid CNO major group, sex or year range")
    if not Path(path).is_file():
        return {"status":"not_imported","country":"ES","group":group,
                "precision":"cno11_major_group","observations":[]}
    series=_source(str(path))[(group,sex)]
    observations=[v for v in series["observations"]
                  if start_year <= v["year"] <= end_year]
    available=[x for x in observations if x["status"]=="available"]
    return {
        "status":"available" if available else "unavailable",
        "country":"ES","group":group,"group_label":series["group_label"],
        "sex":sex,"sex_label":series["sex_label"],
        "precision":"cno11_major_group" if group!="TOTAL" else "all_occupations",
        "classification":"CNO-11: "+group if group!="TOTAL" else "total_employees",
        "currency":"EUR","unit":"EUR/year","salary_concept":"gross_annual_wage",
        "measure":"mean","geography":"national",
        "source":SOURCE,"source_url":SOURCE_URL,
        "source_table":"28186","licence":OPEN_DATA_LICENSE,
        "observations":observations,
        "note":"Group average across multiple professions; never use as the selected profession's salary. Null means suppressed or unavailable. The source's negative sign is a small-sample reliability flag, NOT negative pay."
    }

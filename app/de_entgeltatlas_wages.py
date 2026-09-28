"""Germany BA Entgeltatlas 2025 occupation-specific monthly median wages.

Only manually approved EarnWage occupations whose selected profession belongs
directly to a KldB Berufsgattung are admitted. A BA fallback from Berufsgattung
to the broader Berufsgruppe is never accepted as an exact occupation wage.
Production request paths are offline and read only the committed snapshot.
"""
import json
import math
from pathlib import Path

from app.store import connect

SOURCE = "Statistik der Bundesagentur fuer Arbeit, Entgeltatlas 2025"
HELP_URL = "https://www.arbeitsagentur.de/hilfe-entgeltatlas"
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "de_entgeltatlas_wages.json"
YEAR = "2025"
PRECISION = "occupation_specific_kldb_berufsgattung_no_fallback"
AGGREGATION_LEVEL = "Berufsgattung"

# occupation -> (Entgeltatlas evidence page id, verified national 2025 median EUR/month)
# The snapshot carries the human-readable German profession and Berufsgattung.
APPROVED = {
    "accountant": ("7692", 4451),
    "financial_analyst": ("6779", 6855),
    "doctor": ("58709", 7450),
    "nurse": ("8791", 4587),
    "physiotherapist": ("8748", 3452),
    "preschool_teacher": ("9105", 4314),
    "software_developer": ("134894", 6301),
    "civil_engineer": ("58576", 6038),
    "mechanical_engineer": ("58731", 7084),
    "architect": ("58684", 4950),
    "administrative_assistant": ("15043", 4022),
    "sales_assistant": ("6627", 2976),
    "truck_driver": ("14717", 3196),
    "bus_driver": ("7169", 3733),
    "electrician": ("15637", 3935),
    "plumber": ("15625", 3884),
    "cook": ("3739", 3018),
    "waiter": ("10051", 2652),
    "cleaner": ("10223", 2580),
    "security_guard": ("134232", 3069),
    "lawyer": ("50901", 7922),
    "dentist": ("8702", 6152),
    "healthcare_assistant": ("8874", 3596),
    "cybersecurity_specialist": ("139666", 6313),
    "secondary_teacher": ("9297", 5702),
    "welder": ("2068", 3843),
    "automotive_mechanic": ("137638", 3755),
}
FIELDS = (
    "country", "occupation", "geography", "reference_period", "currency",
    "measure", "unit", "value", "source", "source_url", "evidence_page_id",
    "profession_title", "occupational_aggregate", "requirement_level",
    "aggregation_level", "precision",
)


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 < number < 100000 else None


def validate_snapshot(obj):
    if (not isinstance(obj, dict) or obj.get("schema") != 1 or
            obj.get("source") != SOURCE or obj.get("reference_period") != YEAR or
            obj.get("measure") != "median" or obj.get("geography") != "national" or
            not isinstance(obj.get("records"), list)):
        raise ValueError("Invalid BA Entgeltatlas snapshot metadata")
    rows, seen = [], set()
    for row in obj["records"]:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError("Invalid BA Entgeltatlas row structure")
        approved = APPROVED.get(row.get("occupation"))
        if (approved is None or row.get("country") != "DE" or
                row.get("geography") != "national" or
                row.get("reference_period") != YEAR or
                row.get("currency") != "EUR" or row.get("measure") != "median" or
                row.get("unit") != "EUR/month" or row.get("source") != SOURCE or
                row.get("evidence_page_id") != approved[0] or
                row.get("source_url") !=
                "https://web.arbeitsagentur.de/entgeltatlas/beruf/" + approved[0] or
                _number(row.get("value")) != float(approved[1]) or
                not isinstance(row.get("profession_title"), str) or
                not row["profession_title"].strip() or
                not isinstance(row.get("occupational_aggregate"), str) or
                not row["occupational_aggregate"].strip() or
                row.get("requirement_level") not in
                ("Helfer", "Fachkraft", "Spezialist", "Experte") or
                row.get("aggregation_level") != AGGREGATION_LEVEL or
                row.get("precision") != PRECISION):
            raise ValueError("Unverified BA Entgeltatlas occupation row")
        key = (row["occupation"], row["reference_period"])
        if key in seen:
            raise ValueError("Duplicate BA Entgeltatlas occupation/year")
        seen.add(key)
        rows.append(tuple(row[field] for field in FIELDS))
    if set(seen) != {(job, YEAR) for job in APPROVED}:
        raise ValueError("Incomplete approved BA Entgeltatlas snapshot")
    return rows


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS de_entgeltatlas_wages (
        country TEXT NOT NULL, occupation TEXT NOT NULL, geography TEXT NOT NULL,
        reference_period TEXT NOT NULL, currency TEXT NOT NULL, measure TEXT NOT NULL,
        unit TEXT NOT NULL, value REAL NOT NULL, source TEXT NOT NULL,
        source_url TEXT NOT NULL, evidence_page_id TEXT NOT NULL,
        profession_title TEXT NOT NULL, occupational_aggregate TEXT NOT NULL,
        requirement_level TEXT NOT NULL, aggregation_level TEXT NOT NULL,
        precision TEXT NOT NULL,
        PRIMARY KEY(country, occupation, reference_period, source)
    )""")


def load_snapshot(path=DEFAULT):
    path = Path(path)
    if not path.is_file():
        return 0
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = validate_snapshot(obj)
    with connect() as db:
        init(db)
        db.executemany(
            "INSERT OR REPLACE INTO de_entgeltatlas_wages VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return len(rows)


def observed_coverage():
    with connect() as db:
        init(db)
        rows = db.execute(
            """SELECT occupation,COUNT(*),MAX(reference_period)
               FROM de_entgeltatlas_wages GROUP BY occupation"""
        ).fetchall()
    return {occupation: (count, period) for occupation, count, period in rows}


def wages(country, occupation):
    if country != "DE":
        return {"status": "unavailable", "country": country,
                "occupation": occupation,
                "reason": "BA Entgeltatlas integration applies only to Germany"}
    if occupation not in APPROVED:
        return {"status": "unavailable", "country": "DE",
                "occupation": occupation, "geography": "national",
                "reason": ("No approved direct Berufsgattung mapping; broad or "
                           "ambiguous profession and Berufsgruppe fallbacks are rejected")}
    with connect() as db:
        init(db)
        row = db.execute(
            """SELECT reference_period,currency,measure,unit,value,source,source_url,
                      evidence_page_id,profession_title,occupational_aggregate,
                      requirement_level,aggregation_level,precision
               FROM de_entgeltatlas_wages
               WHERE country='DE' AND occupation=? ORDER BY reference_period DESC""",
            (occupation,),
        ).fetchone()
    if not row:
        return {"status": "unavailable", "country": "DE",
                "occupation": occupation, "geography": "national",
                "reason": "Approved BA Entgeltatlas occupation snapshot not imported"}
    (period, currency, measure, source_unit, value, source, source_url,
     page_id, title, aggregate, level, aggregation, precision) = row
    return {
        "status": "available", "country": "DE", "occupation": occupation,
        "geography": "national", "period": period, "reference_period": period,
        "value": value, "currency": currency,
        "unit": "monthly gross remuneration (median, full-time social-security employees)",
        "source_unit": source_unit, "measure": measure,
        "salary_concept": "social_security_gross_monthly_remuneration",
        "source": source, "source_url": source_url,
        "methodology_url": HELP_URL, "evidence_page_id": page_id,
        "profession_title": title, "occupational_aggregate": aggregate,
        "requirement_level": level, "aggregation_level": aggregation,
        "precision": precision, "preferred_measure": "median",
        "note": ("BA Entgeltatlas 2025 national approximated median monthly gross "
                 "remuneration for the full-time core group. No Berufsgruppe fallback "
                 "is admitted. Annual display, if requested, is monthly x 12 and is "
                 "not a source-published annual salary."),
    }

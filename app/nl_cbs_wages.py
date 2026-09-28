"""Netherlands CBS employee hourly wages by BRC 2014 edition 2025.

The source reports the median GROSS hourly wage. Special payments and overtime
pay are excluded from gross wage; overtime hours and holiday/public-holiday
leave hours are excluded from paid hours. Only manually approved EarnWage to
BRC occupational-group mappings are admitted.
"""
import json
import math
from pathlib import Path

from app.store import connect

SOURCE = "CBS Statistics Netherlands"
DATASET = "86355NED"
SOURCE_URL = "https://datasets.cbs.nl/odata/v1/CBS/86355NED"
SOURCE_PAGE = "https://www.cbs.nl/nl-nl/cijfers/detail/86355NED"
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "nl_cbs_wages.json"
PRECISION = "approved_direct_brc_occupational_group"

# occupation -> (BRC code, CBS identifier, latest verified period, value)
APPROVED = {
    "accountant": ("0411", "A000194", "2025", 38),
    "physiotherapist": ("1013", "A000291", "2025", 32.4),
    "preschool_teacher": ("0132", "A059350", "2024", 21.9),
    "software_developer": ("0814", "A059354", "2025", 34.5),
    "it_technician": ("0821", "A000278", "2025", 25.7),
    "architect": ("0714", "A000244", "2025", 35.5),
    "administrative_assistant": ("0431", "A000204", "2025", 23.3),
    "receptionist": ("0433", "A000206", "2025", 22),
    "sales_assistant": ("0332", "A000189", "2025", 17.3),
    "truck_driver": ("1214", "A000321", "2025", 22.5),
    "electrician": ("0761", "A000267", "2025", 25.1),
    "cook": ("1112", "A000308", "2025", 19),
    "waiter": ("1113", "A000309", "2025", 16.4),
    "cleaner": ("1121", "A000314", "2025", 18.8),
    "security_guard": ("0633", "A000237", "2025", 24.3),
    "healthcare_assistant": ("1051", "A000304", "2025", 25.5),
    "cybersecurity_specialist": ("0812", "A000276", "2025", 34.9),
    "secondary_teacher": ("0113", "A000165", "2024", 35.4),
    "warehouse_operator": ("1223", "A059355", "2025", 11.4),
    "industrial_operator": ("0771", "A000269", "2025", 22.9),
    "automotive_mechanic": ("0743", "A000258", "2025", 23.1),
}

FIELDS = (
    "country", "occupation", "geography", "reference_period",
    "publication_status", "currency", "measure", "unit", "value", "source",
    "source_url", "source_page", "dataset", "classification", "brc_code",
    "cbs_identifier", "brc_label", "employees_thousand", "salary_concept",
    "precision",
)


def _positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def validate_snapshot(obj):
    if (not isinstance(obj, dict) or obj.get("schema") != 1 or
            obj.get("dataset") != DATASET or obj.get("measure") != "median" or
            obj.get("unit") != "EUR/hour gross" or
            not isinstance(obj.get("records"), list)):
        raise ValueError("Invalid CBS Netherlands wage snapshot metadata")

    rows, seen = [], set()
    for row in obj["records"]:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError("Invalid CBS Netherlands wage row structure")
        approved = APPROVED.get(row.get("occupation"))
        if approved is None:
            raise ValueError("Unapproved CBS Netherlands occupation")
        brc, identifier, period, value = approved
        if (
            row.get("country") != "NL" or row.get("geography") != "national" or
            row.get("reference_period") != period or
            row.get("publication_status") not in ("provisional", "definitive") or
            row.get("currency") != "EUR" or row.get("measure") != "median" or
            row.get("unit") != "EUR/hour" or _positive(row.get("value")) != float(value) or
            row.get("source") != SOURCE or row.get("source_url") != SOURCE_URL or
            row.get("source_page") != SOURCE_PAGE or row.get("dataset") != DATASET or
            row.get("classification") != "BRC 2014 editie 2025" or
            row.get("brc_code") != brc or row.get("cbs_identifier") != identifier or
            not isinstance(row.get("brc_label"), str) or not row["brc_label"].strip() or
            _positive(row.get("employees_thousand")) is None or
            row.get("salary_concept") !=
            "gross_hourly_median_excluding_special_pay_and_overtime" or
            row.get("precision") != PRECISION
        ):
            raise ValueError("Unverified CBS Netherlands occupation wage row")
        if period == "2025" and row["publication_status"] != "provisional":
            raise ValueError("CBS 2025 wage must be marked provisional")
        if period == "2024" and row["publication_status"] != "definitive":
            raise ValueError("CBS 2024 wage must be marked definitive")
        key = (row["occupation"], period)
        if key in seen:
            raise ValueError("Duplicate CBS Netherlands occupation/year")
        seen.add(key)
        rows.append(tuple(row[field] for field in FIELDS))

    expected = {(occupation, values[2]) for occupation, values in APPROVED.items()}
    if seen != expected:
        raise ValueError("Incomplete approved CBS Netherlands wage snapshot")
    return rows


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS nl_cbs_wages (
        country TEXT NOT NULL, occupation TEXT NOT NULL, geography TEXT NOT NULL,
        reference_period TEXT NOT NULL, publication_status TEXT NOT NULL,
        currency TEXT NOT NULL, measure TEXT NOT NULL, unit TEXT NOT NULL,
        value REAL NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL,
        source_page TEXT NOT NULL, dataset TEXT NOT NULL,
        classification TEXT NOT NULL, brc_code TEXT NOT NULL,
        cbs_identifier TEXT NOT NULL, brc_label TEXT NOT NULL,
        employees_thousand REAL NOT NULL, salary_concept TEXT NOT NULL,
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
            "INSERT OR REPLACE INTO nl_cbs_wages VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return len(rows)


def observed_coverage():
    with connect() as db:
        init(db)
        rows = db.execute(
            """SELECT occupation,COUNT(*),MAX(reference_period)
               FROM nl_cbs_wages GROUP BY occupation"""
        ).fetchall()
    return {occupation: (count, period) for occupation, count, period in rows}


def wages(country, occupation):
    if country != "NL":
        return {"status": "unavailable", "country": country,
                "occupation": occupation,
                "reason": "CBS Netherlands integration applies only to NL"}
    if occupation not in APPROVED:
        return {
            "status": "unavailable", "country": "NL", "occupation": occupation,
            "geography": "national",
            "reason": (
                "No approved direct BRC occupational-group wage: the CBS group "
                "is too broad/split for this EarnWage occupation or the median "
                "is not published"
            ),
        }

    with connect() as db:
        init(db)
        row = db.execute(
            """SELECT reference_period,publication_status,currency,measure,unit,
                      value,source,source_url,source_page,dataset,classification,
                      brc_code,cbs_identifier,brc_label,employees_thousand,
                      salary_concept,precision
               FROM nl_cbs_wages
               WHERE country='NL' AND occupation=?
               ORDER BY reference_period DESC""",
            (occupation,),
        ).fetchone()

    if not row:
        return {
            "status": "unavailable", "country": "NL", "occupation": occupation,
            "geography": "national",
            "reason": "Approved CBS Netherlands occupation snapshot not imported",
        }

    (period, publication_status, currency, measure, unit, value, source,
     source_url, source_page, dataset, classification, brc_code,
     cbs_identifier, brc_label, employees_thousand, salary_concept,
     precision) = row
    return {
        "status": "available", "country": "NL", "occupation": occupation,
        "geography": "national", "period": period, "reference_period": period,
        "publication_status": publication_status,
        "value": value, "currency": currency,
        "unit": "gross hourly wage (median)",
        "source_unit": unit, "measure": measure,
        "salary_concept": salary_concept,
        "source": source, "source_url": source_url, "source_page": source_page,
        "dataset": dataset, "classification": classification + ":" + brc_code,
        "brc_code": brc_code, "cbs_identifier": cbs_identifier,
        "brc_label": brc_label, "employees_thousand": employees_thousand,
        "precision": precision, "preferred_measure": "median",
        "note": (
            "CBS median gross hourly wage for employees aged 15 to 74 in their "
            "main job. Gross wage excludes special payments and overtime pay. "
            "No monthly or annual salary is inferred from the hourly observation. "
            + ("2025 is provisional." if publication_status == "provisional"
               else "2024 is definitive.")
        ),
    }

"""France INSEE 2024 detailed private-sector occupation wages.

The source reports mean NET monthly salary in full-time equivalent (EQTP).
Only manually approved EarnWage mappings to one detailed PCS-ESE category are
admitted. Production requests use only the committed validated snapshot.
"""
import json
import math
from pathlib import Path

from app.store import connect

SOURCE = "INSEE, Base Tous salaries 2024"
DATASET = "DS_DERA_PRIVE_ANNUEL"
SOURCE_URL = (
    "https://api.insee.fr/melodi/file/DS_DERA_PRIVE_ANNUEL/"
    "DS_DERA_PRIVE_ANNUEL_2024_CSV_FR"
)
DATASET_PAGE = (
    "https://www.data.gouv.fr/datasets/"
    "salaires-dans-le-secteur-prive-par-categorie-socioprofessionnelle-detaillee"
)
DEFAULT = Path(__file__).resolve().parent.parent / "data" / "fr_insee_wages.json"
YEAR = "2024"
PRECISION = "approved_direct_pcs_ese_mapping"

# occupation -> (PCS-ESE code, verified 2024 national mean net EUR/month EQTP)
APPROVED = {
    "doctor": ("344B", 7125.42),
    "nurse": ("431F", 2715.20),
    "pharmacist": ("344D", 4023.55),
    "psychologist": ("311D", 2807.58),
    "physiotherapist": ("432B", 2731.72),
    "preschool_teacher": ("434G", 1948.70),
    "it_technician": ("478C", 2380.11),
    "civil_engineer": ("382A", 3863.89),
    "mechanical_engineer": ("384A", 4183.50),
    "architect": ("382B", 3531.84),
    "supermarket_worker": ("551A", 1756.10),
    "truck_driver": ("641A", 2247.12),
    "bus_driver": ("641B", 2353.86),
    "electrician": ("633A", 2116.03),
    "plumber": ("632F", 2160.77),
    "cook": ("636D", 1980.60),
    "cleaner": ("684A", 1700.12),
    "security_guard": ("534A", 1954.40),
    "lawyer": ("312A", 5335.77),
    "dentist": ("311C", 7363.56),
    "healthcare_assistant": ("526A", 2153.20),
    "welder": ("623E", 2256.68),
    "automotive_mechanic": ("634C", 2084.36),
}

FIELDS = (
    "country", "occupation", "geography", "reference_period", "currency",
    "measure", "unit", "value", "source", "source_url", "dataset", "pcs_ese",
    "pcs_ese_label", "pcs_ese_url", "fte_count", "salary_concept",
    "employment_scope", "precision",
)


def _positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def validate_snapshot(obj):
    if (not isinstance(obj, dict) or obj.get("schema") != 1 or
            obj.get("dataset") != DATASET or obj.get("reference_period") != YEAR or
            obj.get("measure") != "mean" or
            obj.get("unit") != "EUR/month net EQTP" or
            not isinstance(obj.get("records"), list)):
        raise ValueError("Invalid INSEE France wage snapshot metadata")

    rows, seen = [], set()
    for row in obj["records"]:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError("Invalid INSEE France wage row structure")
        approved = APPROVED.get(row.get("occupation"))
        code = row.get("pcs_ese")
        if (approved is None or row.get("country") != "FR" or
                row.get("geography") != "national" or
                row.get("reference_period") != YEAR or
                row.get("currency") != "EUR" or row.get("measure") != "mean" or
                row.get("unit") != "EUR/month" or row.get("source") != SOURCE or
                row.get("source_url") != SOURCE_URL or row.get("dataset") != DATASET or
                code != approved[0] or
                row.get("pcs_ese_url") !=
                "https://www.insee.fr/fr/metadonnees/pcsese2003/rubriqueRegroupee/" +
                approved[0].lower() or
                _positive_number(row.get("value")) != float(approved[1]) or
                _positive_number(row.get("fte_count")) is None or
                not isinstance(row.get("pcs_ese_label"), str) or
                not row["pcs_ese_label"].strip() or
                row.get("salary_concept") !=
                "net_monthly_mean_full_time_equivalent" or
                row.get("employment_scope") != "private_sector_employees" or
                row.get("precision") != PRECISION):
            raise ValueError("Unverified INSEE France occupation row")
        key = (row["occupation"], row["reference_period"])
        if key in seen:
            raise ValueError("Duplicate INSEE France occupation/year")
        seen.add(key)
        rows.append(tuple(row[field] for field in FIELDS))

    if set(seen) != {(job, YEAR) for job in APPROVED}:
        raise ValueError("Incomplete approved INSEE France wage snapshot")
    return rows


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS fr_insee_wages (
        country TEXT NOT NULL, occupation TEXT NOT NULL, geography TEXT NOT NULL,
        reference_period TEXT NOT NULL, currency TEXT NOT NULL, measure TEXT NOT NULL,
        unit TEXT NOT NULL, value REAL NOT NULL, source TEXT NOT NULL,
        source_url TEXT NOT NULL, dataset TEXT NOT NULL, pcs_ese TEXT NOT NULL,
        pcs_ese_label TEXT NOT NULL, pcs_ese_url TEXT NOT NULL, fte_count REAL NOT NULL,
        salary_concept TEXT NOT NULL, employment_scope TEXT NOT NULL,
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
            "INSERT OR REPLACE INTO fr_insee_wages VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return len(rows)


def observed_coverage():
    with connect() as db:
        init(db)
        rows = db.execute(
            """SELECT occupation,COUNT(*),MAX(reference_period)
               FROM fr_insee_wages GROUP BY occupation"""
        ).fetchall()
    return {occupation: (count, period) for occupation, count, period in rows}


def wages(country, occupation):
    if country != "FR":
        return {"status": "unavailable", "country": country,
                "occupation": occupation,
                "reason": "INSEE France integration applies only to France"}
    if occupation not in APPROVED:
        return {
            "status": "unavailable", "country": "FR", "occupation": occupation,
            "geography": "national",
            "reason": (
                "No approved direct PCS-ESE mapping in this private-sector dataset; "
                "ambiguous, split or predominantly public occupations are rejected"
            ),
        }

    with connect() as db:
        init(db)
        row = db.execute(
            """SELECT reference_period,currency,measure,unit,value,source,source_url,
                      dataset,pcs_ese,pcs_ese_label,pcs_ese_url,fte_count,
                      salary_concept,employment_scope,precision
               FROM fr_insee_wages
               WHERE country='FR' AND occupation=?
               ORDER BY reference_period DESC""",
            (occupation,),
        ).fetchone()

    if not row:
        return {
            "status": "unavailable", "country": "FR", "occupation": occupation,
            "geography": "national",
            "reason": "Approved INSEE France occupation snapshot not imported",
        }

    (period, currency, measure, source_unit, value, source, source_url,
     dataset, pcs, label, pcs_url, fte_count, salary_concept,
     employment_scope, precision) = row

    return {
        "status": "available", "country": "FR", "occupation": occupation,
        "geography": "national", "period": period, "reference_period": period,
        "value": value, "currency": currency,
        "unit": "monthly net salary (mean, full-time equivalent, private employees)",
        "source_unit": source_unit, "measure": measure,
        "salary_concept": salary_concept,
        "employment_scope": employment_scope,
        "source": source, "source_url": source_url,
        "dataset": dataset, "dataset_page": DATASET_PAGE,
        "classification": "PCS-ESE 2003:" + pcs,
        "pcs_ese": pcs, "pcs_ese_label": label, "pcs_ese_url": pcs_url,
        "fte_count": fte_count, "precision": precision,
        "preferred_measure": "mean",
        "note": (
            "INSEE Base Tous salaries 2024: mean NET monthly salary in EQTP for "
            "private-sector employees. The source excludes agriculture employees "
            "and individual employers. For occupations also common in the public "
            "sector or self-employment, only the private salaried population is "
            "represented. Any annual display is monthly x 12 and is not a "
            "source-published annual salary."
        ),
    }

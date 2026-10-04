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
               else period + " is definitive.")
        ),
    }


# Official files obtained during PR #34; no network requests on API paths.
# Updating this release requires a new source/license/classification review.
HISTORY_VERSION = '202608180000'
HISTORY_LICENCE = 'https://creativecommons.org/licenses/by/4.0/'
HISTORY_SOURCES = {
    'properties': ('Properties', 'fd21a86a3decc9f2943a4309d0cea2e33e5bf0b08a2e5a250158277a2e130b55'),
    'occupation_codes': ('BeroepCodes', 'f8c5404dadcf35b5f2d41d3c1763335cb8ab8861c8e1ced359dcef8c214b724f'),
    'period_codes': ('PeriodenCodes', '9f36fe7c9f8075bb7e82bf5ae61285f1e66a9b2749a01935b88ce08099ff1a61'),
    'measure_codes': ('MeasureCodes', '8f4f7bf1299f18e92b9632a3d6b1fbafc4a5efa4ce7d632ecdad4c801307ba71'),
    'observations': ('Observations', '097c2dbe156374aee00623f86570a0c5808e26a1329cff3566b7d2f30453053c'),
}
# Metadata timestamps are recorded request starts; the observations timestamp
# records completion of the complete download. They are not inferred from mtime.
HISTORY_SOURCE_DATES = {
    'properties': '2026-10-04T13:41:45.795218+00:00',
    'occupation_codes': '2026-10-04T13:41:46.881516+00:00',
    'period_codes': '2026-10-04T13:41:47.732447+00:00',
    'measure_codes': '2026-10-04T13:41:47.929349+00:00',
    'observations': '2026-10-04T13:43:35.954865+00:00',
}

# Canonical derived records are pinned independently of caller-supplied hashes.
HISTORY_RECORDS_SHA256 = 'db0749c813011b5515b66f76fab769f64071e7511d32af8c200bff7fd932df66'


def _history_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate CBS JSON key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-finite CBS JSON constant')

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def _records_digest(records):
    import hashlib
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_history_review(source_directory, acquired_at):
    """Reproduce a private review from complete, independently pinned files.

    No download, DB connection, mapping expansion or production publication.
    Missing source observations remain exclusions, never fabricated zeros.
    """
    import hashlib
    from datetime import datetime
    from decimal import Decimal
    acquired = datetime.fromisoformat(acquired_at)
    if acquired.tzinfo is None or acquired != datetime.fromisoformat(HISTORY_SOURCE_DATES['observations']):
        raise ValueError('Original reviewed acquisition timestamp with timezone required')
    root = Path(source_directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Explicit regular source directory required')
    objects, artifacts = {}, []
    for name, (entity, checksum) in HISTORY_SOURCES.items():
        path = root / ('NL-' + name + '.body')
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 5 * 1024 * 1024:
            raise ValueError('Missing or unsafe CBS source file: ' + name)
        with path.open('rb') as source:
            raw = source.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError('CBS source exceeds size limit')
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError('Unreviewed CBS source checksum: ' + name)
        objects[name] = _history_json(raw)
        artifacts.append({'url': SOURCE_URL + '/' + entity, 'sha256': checksum,
                          'bytes': len(raw), 'fetched_at': HISTORY_SOURCE_DATES[name],
                          'timestamp_basis': 'download_completion' if name == 'observations' else 'recorded_request_start',
                          'source_version': HISTORY_VERSION, 'licence_url': HISTORY_LICENCE,
                          'acquisition_mode': 'previous_live_download_reused'})
    properties = objects['properties']
    if (properties.get('Identifier') != DATASET or properties.get('Source') != 'CBS.'
            or properties.get('Version') != HISTORY_VERSION
            or properties.get('License') != HISTORY_LICENCE
            or properties.get('TemporalCoverage') != '2013-2025'
            or 'BRC 2014 editie 2025' not in properties.get('Description', '')):
        raise ValueError('Unreviewed CBS release metadata, licence or classification')

    def codes(name):
        obj = objects[name]
        if '@odata.nextLink' in obj or not isinstance(obj.get('value'), list):
            raise ValueError('Incomplete CBS metadata')
        result = {}
        for row in obj['value']:
            if row['Identifier'] in result:
                raise ValueError('Duplicate CBS metadata identifier')
            result[row['Identifier']] = row
        return result

    periods, occupations, measures = codes('period_codes'), codes('occupation_codes'), codes('measure_codes')
    if set(periods) != {str(year) + 'JJ00' for year in range(2013, 2026)}:
        raise ValueError('Unexpected CBS period universe')
    for code, period in periods.items():
        year = code[:4]
        expected = 'Voorlopig' if year == '2025' else 'Definitief'
        if period.get('Title') != year or period.get('Status') != expected:
            raise ValueError('Unreviewed CBS period/status')
    median, workers = measures.get('A043068', {}), measures.get('A045285', {})
    if (median.get('Title') != '50e percentiel (mediaan)' or median.get('Unit') != 'euro'
            or workers.get('Unit') != 'x 1 000'):
        raise ValueError('Unexpected CBS salary or employee-count measure')
    templates = {row['occupation']: row for row in _history_json(DEFAULT.read_bytes())['records']}
    indexed_jobs = {identifier: (occupation, brc)
                    for occupation, (brc, identifier, _, _) in APPROVED.items()}
    for identifier, (_, brc) in indexed_jobs.items():
        if not occupations.get(identifier, {}).get('Title', '').startswith(brc + ' '):
            raise ValueError('CBS occupation identity drift')
    obj = objects['observations']
    source_rows = obj.get('value')
    if ('@odata.nextLink' in obj or not isinstance(source_rows, list)
            or type(properties.get('ObservationCount')) is not int
            or len(source_rows) != properties['ObservationCount']):
        raise ValueError('Incomplete CBS observations')
    indexed, seen_ids = {}, set()
    fields = {'Id', 'Measure', 'ValueAttribute', 'Value', 'StringValue', 'Beroep', 'Perioden'}
    for row in source_rows:
        if (set(row) != fields or type(row['Id']) is not int or row['Id'] < 0
                or row['Id'] in seen_ids or row['Measure'] not in measures
                or row['Beroep'] not in occupations or row['Perioden'] not in periods):
            raise ValueError('Unexpected CBS observation schema or dimension')
        seen_ids.add(row['Id'])
        key = (row['Beroep'], row['Perioden'], row['Measure'])
        if key in indexed:
            raise ValueError('Duplicate CBS observation dimensions')
        indexed[key] = row
    records, provenance, exclusions = [], [], []
    for identifier, (occupation, _) in sorted(indexed_jobs.items()):
        for code, period in sorted(periods.items()):
            median = indexed.get((identifier, code, 'A043068'))
            workers = indexed.get((identifier, code, 'A045285'))
            if median is None:
                exclusions.append({'occupation': occupation, 'period': period['Title'],
                                   'reason': 'absent_source_observation', 'value': None})
                continue
            if (median['ValueAttribute'] != 'None' or median['StringValue'] is not None
                    or median['Value'] is None):
                exclusions.append({'occupation': occupation, 'period': period['Title'],
                                   'reason': 'missing_or_flagged_source_observation', 'value': None,
                                   'original': median})
                continue
            value = _positive(median['Value'])
            if (type(median['Value']) not in (int, float) or value is None
                    or workers is None or workers['ValueAttribute'] != 'None'
                    or workers['StringValue'] is not None
                    or type(workers['Value']) not in (int, float) or _positive(workers['Value']) is None):
                raise ValueError('Invalid CBS salary or employee count')
            record = {**templates[occupation], 'reference_period': period['Title'],
                      'publication_status': 'provisional' if period['Status'] == 'Voorlopig' else 'definitive',
                      'value': str(Decimal(str(median['Value']))),
                      'employees_thousand': str(Decimal(str(workers['Value'])))}
            records.append(record)
            provenance.append({'occupation': occupation, 'period': period['Title'],
                               'original_period': code, 'period_status': period['Status'],
                               'period_description': period['Description'],
                               'salary_observation': median, 'employee_observation': workers})
    records.sort(key=lambda row: (row['occupation'], row['reference_period']))
    provenance.sort(key=lambda row: (row['occupation'], row['period']))
    if not records:
        raise ValueError('No CBS historical salaries')
    return {'schema': 'earnwage-cbs-history-review-v1', 'dataset': DATASET,
            'source_version': HISTORY_VERSION, 'licence_url': HISTORY_LICENCE,
            'acquired_at': acquired_at, 'artifacts': artifacts, 'records': records,
            'records_sha256': _records_digest(records), 'provenance': provenance,
            'exclusions': exclusions, 'source_observations': len(source_rows),
            'scope': 'offline_review_not_production_publication'}


def validate_history_review(review):
    """Fail closed on caller-rehashed modifications to the reviewed release."""
    if not isinstance(review, dict):
        raise ValueError('CBS history review must be an object')
    from datetime import datetime
    if not isinstance(review.get('acquired_at'), str) or datetime.fromisoformat(review['acquired_at']) != datetime.fromisoformat(HISTORY_SOURCE_DATES['observations']):
        raise ValueError('Explicit acquisition timestamp and timezone required')
    dates = {SOURCE_URL + '/' + entity: HISTORY_SOURCE_DATES[name]
             for name, (entity, _) in HISTORY_SOURCES.items()}
    if not isinstance(review.get('artifacts'), list) or any(
            not isinstance(item, dict) or item.get('fetched_at') != dates.get(item.get('url'))
            for item in review['artifacts']):
        raise ValueError('Inconsistent CBS acquisition provenance')
    if (review.get('schema') != 'earnwage-cbs-history-review-v1'
            or review.get('dataset') != DATASET or review.get('source_version') != HISTORY_VERSION
            or review.get('licence_url') != HISTORY_LICENCE
            or _records_digest(review.get('records')) != HISTORY_RECORDS_SHA256
            or review.get('records_sha256') != HISTORY_RECORDS_SHA256):
        raise ValueError('Unreviewed or modified CBS historical release')
    # Provenance, exclusions and metadata must also reproduce the reviewed bundle.
    if history_review_digest(review) != HISTORY_REVIEW_SHA256:
        raise ValueError('Modified CBS history provenance or completeness')
    return [tuple(row[field] for field in FIELDS) for row in review['records']]


def history_review_digest(review):
    # Acquisition timestamp is explicitly supplied; it cannot authenticate values.
    normalized = {key: value for key, value in review.items() if key != 'acquired_at'}
    normalized['artifacts'] = [{key: value for key, value in item.items() if key != 'fetched_at'}
                               for item in review.get('artifacts', [])]
    return _records_digest(normalized)


HISTORY_REVIEW_SHA256 = '00f7f8952473278b930becb1771337b23ccc6bfbb4b3c75ec8631b9a91dce02c'


def stage_history_review(store, review):
    """Use the existing BulkStore ledger, checkpoints and quarantine policy."""
    validate_history_review(review)
    run_id = store.start('cbs', DATASET)
    try:
        for artifact in review['artifacts']:
            store.artifact(artifact)
        original = {(r['occupation'], r['period']): r for r in review['provenance']}
        def observations():
            for row in review['records']:
                source = original[row['occupation'], row['reference_period']]
                yield {'provider': 'cbs', 'dataset': DATASET, 'country': 'NL',
                       'geography': 'national', 'indicator': 'occupational_salary',
                       'classification': 'BRC2014_ed2025:' + row['brc_code'],
                       'occupations': [row['occupation']], 'measure': 'median',
                       'unit': 'EUR/hour', 'currency': 'EUR', 'period': row['reference_period'],
                       'value': row['value'], 'source_url': SOURCE_URL + '/Observations',
                       'source_version': HISTORY_VERSION, 'licence_url': HISTORY_LICENCE,
                       'publication_status': row['publication_status'], 'flags': '',
                       'precision': PRECISION, 'original': source,
                       'dimensions': {'classification_version': 'BRC2014_ed2025',
                                      'salary_concept': row['salary_concept'],
                                      'population': 'employees_15_74_main_job'}}
        counts = store.ingest('cbs:' + DATASET + ':' + HISTORY_VERSION,
                              HISTORY_SOURCES['observations'][1], observations())
        result = {**counts, 'selected': len(review['records']),
                  'excluded': len(review['exclusions']), 'source_version': HISTORY_VERSION,
                  'acquisition_mode': 'previous_live_download_reused',
                  'production_compared': False, 'publication_eligible': False}
        store.finish(run_id, 'complete', result=result)
        return result
    except Exception as error:
        store.finish(run_id, 'failed', type(error).__name__)
        raise

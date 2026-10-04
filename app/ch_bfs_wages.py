"""Swiss FSO ESS historical CH-ISCO-19 sub-major-group wage context.

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
    if p.stat().st_size > 5_000_000:
        raise ValueError("Oversized Swiss snapshot")
    data=json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or data.get("table")!=TABLE:
        raise ValueError("Unsupported Swiss FSO wage snapshot")
    if data.get("publication_status") == "private_staging_only" and p.resolve() == DEFAULT.resolve():
        return []
    rows = data.get("observations", [])
    if not isinstance(rows, list):
        raise ValueError("Invalid Swiss observations")
    identities = set()
    from decimal import Decimal, InvalidOperation
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid Swiss observation")
        identity = tuple(row.get(k) for k in
                         ("period", "geography", "ch_isco19_submajor_group", "age", "sex", "percentile"))
        if None in identity or identity in identities:
            raise ValueError("Incomplete or duplicate Swiss observation")
        identities.add(identity)
        value = row.get("value")
        if row.get("source_status") and value is not None:
            raise ValueError("Flagged Swiss salary cannot be accepted")
        if value is not None:
            try:
                amount = Decimal(str(value))
                if isinstance(value, bool) or not amount.is_finite() or not 0 < amount < 1000000:
                    raise ValueError("Invalid Swiss salary")
            except InvalidOperation as exc:
                raise ValueError("Invalid Swiss salary") from exc
    return rows

def context(occupation,path=DEFAULT, *, period=None, geography="national"):
    group=SUBMAJOR.get(occupation)
    if not group:
        return {"status":"unavailable","country":"CH","occupation":occupation,
                "precision":"ch_isco19_submajor_group"}
    rows=[r for r in load_snapshot(path) if r.get("ch_isco19_submajor_group")==group
          and r.get("geography")==("Switzerland" if geography == "national" else geography) and r.get("age")=="total"
          and r.get("sex")=="total"]
    if not rows:
        return {"status":"unavailable","country":"CH","occupation":occupation,
                "ch_isco19_submajor_group":group,"precision":"ch_isco19_submajor_group",
                "source":SOURCE,"source_url":SOURCE_URL,
                "reason":"Official Swiss group snapshot not imported yet"}
    if period is not None:
        rows = [r for r in rows if str(r["period"]) == str(period)]
        if not rows:
            return {"status":"unavailable", "country":"CH", "occupation":occupation,
                    "precision":"ch_isco19_submajor_group", "reason":"Requested period unavailable"}
    period=max(str(r["period"]) for r in rows)
    selected=[r for r in rows if str(r["period"])==period]
    values={r["percentile"]:r["value"] for r in selected if r.get("value") is not None}
    if values.get("median") is None:
        return {"status":"unavailable", "country":"CH", "occupation":occupation,
                "period":period, "geography":geography,
                "precision":"ch_isco19_submajor_group",
                "reason":"Requested median missing, suppressed or requiring review"}
    return {"status":"available","country":"CH","occupation":occupation,"period":period,
            "ch_isco19_submajor_group":group,"precision":"ch_isco19_submajor_group",
            "geography":geography,"currency":"CHF",
            "unit":"standardised gross monthly wage","values":values,
            "preferred_measure":"median","value":values.get("median"),
            "source":SOURCE,"dataset":TABLE,"source_url":SOURCE_URL,
            "mapping_caution":CAUTION.get(occupation),
            "note":"Official CH-ISCO-19 2-digit group context, not an individual occupation wage. Full-time equivalent: 4 1/3 weeks at 40 hours; includes 1/12 of 13th salary and annual special payments."}

def observed_coverage(path=DEFAULT):
    rows=load_snapshot(path)
    groups={r.get("ch_isco19_submajor_group") for r in rows
            if r.get("geography")=="Switzerland" and r.get("age")=="total"
            and r.get("sex")=="total" and r.get("percentile")=="median"
            and r.get("value") is not None}
    return {job for job,group in SUBMAJOR.items() if group in groups}

# Reviewed against the French metadata and footnotes acquired 2026-10-04.
API_URL = 'https://www.pxweb.bfs.admin.ch/api/v1/fr/' + TABLE + '/' + TABLE + '.px'
AXES = ('Jahr', 'Grossregion', 'Berufsgruppe', 'Lebensalter', 'Geschlecht',
        'Zentralwert und andere Perzentile')
REGIONS = {'-1': 'Suisse', '1': 'Région lémanique', '2': 'Espace Mittelland',
           '3': 'Nordwestschweiz', '4': 'Zürich', '5': 'Ostschweiz',
           '6': 'Zentralschweiz', '7': 'Ticino'}
PERCENTILES = {'1': ('Médiane', 'median'), '2': ('P10', 'p10'),
               '3': ('P25', 'p25'), '4': ('P75', 'p75'), '5': ('P90', 'p90')}


def reviewed_query(metadata):
    """Select published historical groups/regions with explicit population totals."""
    variables = metadata['variables']
    if len(variables) != len(AXES) or {v['code'] for v in variables} != set(AXES):
        raise ValueError('Unexpected BFS dimensions')
    query = []
    for variable in variables:
        code = variable['code']
        values, labels = variable['values'], variable['valueTexts']
        if len(values) != len(labels) or len(set(values)) != len(values):
            raise ValueError('Invalid BFS categories')
        if code in ('Lebensalter', 'Geschlecht'):
            expected = 'Âge - total' if code == 'Lebensalter' else 'Sexe - total'
            if '-1' not in values or labels[values.index('-1')] != expected:
                raise ValueError('Missing explicit population total')
            selected = ['-1']
        elif code == 'Berufsgruppe':
            selected = [v for v, label in zip(values, labels)
                        if len(v) == 2 and v.isdigit() and label.startswith('> ' + v + ' ')]
            if not selected:
                raise ValueError('No documented sub-major groups')
        elif code == 'Jahr':
            if any(v not in {str(y) for y in range(2012, 2025, 2)} for v in values):
                raise ValueError('Unreviewed BFS survey year')
            selected = values
        elif code == 'Grossregion':
            if dict(zip(values, labels)) != REGIONS:
                raise ValueError('Unreviewed BFS geography')
            selected = values
        else:
            if dict(zip(values, labels)) != {k: v[0] for k, v in PERCENTILES.items()}:
                raise ValueError('Unreviewed BFS measures')
            selected = values
        query.append({'code': code, 'selection': {'filter': 'item', 'values': selected}})
    return {'query': query, 'response': {'format': 'json-stat'}}


def import_snapshot(metadata, payload, provenance):
    """Normalize an original BFS cube; suppressed/uncertain cells stay missing.

    This is the existing snapshot model, not a database/publication adapter.
    Raw values and flags remain available for review, never promoted to exact jobs.
    """
    from decimal import Decimal
    from itertools import product
    from math import prod
    import re

    query = reviewed_query(metadata)
    if provenance.get('url') != API_URL or provenance.get('status') != 200:
        raise ValueError('Unverified BFS source endpoint')
    for name in ('sha256', 'query_sha256', 'metadata_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', provenance.get(name, '')):
            raise ValueError('Missing original checksum')
    if not provenance.get('acquired_at'):
        raise ValueError('Missing acquisition date')
    cube = payload.get('dataset', payload)
    dimensions = cube['dimension']
    ids = cube.get('id', dimensions.get('id'))
    sizes = cube.get('size', dimensions.get('size'))
    if not isinstance(ids, list) or len(ids) != len(AXES) or set(ids) != set(AXES):
        raise ValueError('Unexpected cube dimensions')
    if cube.get('source') != 'OFS - Enquête suisse sur la structure des salaires - © OFS':
        raise ValueError('Unexpected BFS statistical source')
    if not isinstance(sizes, list) or len(sizes) != len(ids):
        raise ValueError('Invalid cube shape')
    selected = {q['code']: q['selection']['values'] for q in query['query']}
    axes = []
    for code, size in zip(ids, sizes):
        category = dimensions[code]['category']
        index = category['index']
        if not isinstance(index, dict) or type(size) is not int or size <= 0:
            raise ValueError('Invalid cube index')
        if len(index) != size or sorted(index.values()) != list(range(size)):
            raise ValueError('Incomplete cube categories')
        ordered = sorted(index, key=index.get)
        if ordered != selected[code]:
            raise ValueError('Response does not match reviewed query')
        original = next(v for v in metadata['variables'] if v['code'] == code)
        labels = dict(zip(original['values'], original['valueTexts']))
        if any(category.get('label', {}).get(v) != labels[v] for v in ordered):
            raise ValueError('Changed category semantics')
        axes.append(ordered)
    values = cube['value']
    if not isinstance(values, list) or len(values) != prod(sizes) or len(values) > 20000:
        raise ValueError('Incomplete or oversized BFS cube')
    statuses = cube.get('status', {})
    if not isinstance(statuses, dict) or any(
            not str(k).isdigit() or not 0 <= int(k) < len(values) for k in statuses):
        raise ValueError('Invalid status index')
    rows = []
    for flat, combination in enumerate(product(*axes)):
        codes = dict(zip(ids, combination))
        flag, value = statuses.get(str(flat)), values[flat]
        if flag not in (None, 'X', '...', '( )'):
            raise ValueError('Unreviewed statistical flag')
        if flag in ('X', '...') and value is not None:
            raise ValueError('Suppressed cell carries a salary')
        if value is not None and (type(value) not in (int, float) or
                not Decimal(str(value)).is_finite() or not 0 < Decimal(str(value)) < 1000000):
            raise ValueError('Invalid salary value')
        geo = codes['Grossregion']
        rows.append({'period': codes['Jahr'], 'reference_month': 'October',
                     'geography': 'Switzerland' if geo == '-1' else 'CH:great_region:' + geo,
                     'geography_code': geo, 'geography_label': REGIONS[geo],
                     'ch_isco19_submajor_group': codes['Berufsgruppe'],
                     'group_label': dimensions['Berufsgruppe']['category']['label'][codes['Berufsgruppe']],
                     'age': 'total', 'sex': 'total',
                     'percentile': PERCENTILES[codes[AXES[-1]]][1],
                     'value': value if flag is None else None,
                     'original_value': value, 'source_status': flag,
                     'quality_status': 'review_required' if flag == '( )' else
                                       'suppressed' if flag == 'X' else
                                       'missing' if value is None else 'accepted'})
    return {'schema_version': 1, 'country': 'CH', 'source': SOURCE, 'table': TABLE,
            'currency': 'CHF', 'unit': 'standardised gross monthly wage',
            'sector': 'private_and_public', 'full_time_equivalent': True,
            'weeks_per_month': '4 1/3', 'hours_per_week': 40,
            'provenance': provenance, 'source_reported_updated': cube.get('updated'),
            'methodology_database_date': '2026-02-24',
            'licence_status': 'redistribution_terms_not_verified',
            'publication_status': 'private_staging_only', 'observations': rows}


def decode_snapshot(metadata_bytes, data_bytes, query_bytes, provenance):
    """Check original bytes before normalization, with a bounded, exact query."""
    import hashlib
    if any(not isinstance(b, bytes) or not 0 < len(b) <= 5_000_000
           for b in (metadata_bytes, data_bytes, query_bytes)):
        raise ValueError('Invalid original file size')
    for body, field in ((metadata_bytes, 'metadata_sha256'), (data_bytes, 'sha256'),
                        (query_bytes, 'query_sha256')):
        if hashlib.sha256(body).hexdigest() != provenance.get(field):
            raise ValueError('Original checksum mismatch')
    metadata = json.loads(metadata_bytes)
    if json.loads(query_bytes) != reviewed_query(metadata):
        raise ValueError('Unreviewed query')
    return import_snapshot(metadata, json.loads(data_bytes), provenance)

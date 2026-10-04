"""Pinned CBS release evidence for the existing salary publication mechanism."""
from decimal import Decimal
from app import nl_cbs_wages as nl
from app.bulk_core import observation_key

# This version remains held for review in the audited PR #35 staging.
HELD = {('warehouse_operator', '2023')}


def reviewed_index(review):
    nl.validate_history_review(review)
    originals = {(r['occupation'], r['period']): r for r in review['provenance']}
    index = {}
    for record in review['records']:
        row = {'provider': 'cbs', 'dataset': nl.DATASET, 'country': 'NL',
               'geography': 'national', 'indicator': 'occupational_salary',
               'classification': 'BRC2014_ed2025:' + record['brc_code'],
               'occupations': [record['occupation']], 'measure': 'median',
               'unit': 'EUR/hour', 'currency': 'EUR', 'period': record['reference_period'],
               'value': record['value'], 'source_url': nl.SOURCE_URL + '/Observations',
               'source_version': nl.HISTORY_VERSION, 'licence_url': nl.HISTORY_LICENCE,
               'publication_status': record['publication_status'], 'flags': '',
               'precision': nl.PRECISION,
               'original': originals[record['occupation'], record['reference_period']],
               'dimensions': {'classification_version': 'BRC2014_ed2025',
                              'salary_concept': record['salary_concept'],
                              'population': 'employees_15_74_main_job'},
               'artifact_sha256': nl.HISTORY_SOURCES['observations'][1]}
        index[observation_key(row)] = (row, record)
    return index


def projection(row, index):
    if index is None:
        raise ValueError('Pinned CBS history review required')
    entry = index.get(observation_key(row))
    if entry is None or row != entry[0]:
        raise ValueError('CBS observation differs from pinned release evidence')
    record = entry[1]
    if (record['occupation'], record['reference_period']) in HELD:
        raise ValueError('CBS observation remains in quarantine')
    base = dict(record)
    # Native target schema stores REAL; exact conversion is required, not lossy.
    for field in ('value', 'employees_thousand'):
        number = Decimal(base[field])
        if Decimal(str(float(number))) != number:
            raise ValueError('CBS numeric value cannot be represented by target schema')
        base[field] = float(number)
    identity = {k: base[k] for k in ('country', 'occupation', 'reference_period', 'source')}
    return [('nl_cbs_wages', identity, base, 'value', record['value'])], None

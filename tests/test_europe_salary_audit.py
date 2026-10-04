"""Keep the investigation consistent with the existing read-only inventory.

No private source downloads or production databases are needed by CI.
"""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from app.bulk_coverage import build_report
from app.catalog import COUNTRY_MAP, OCCUPATIONS

ROOT = Path(__file__).resolve().parent.parent
REPORT = json.loads((ROOT/'docs/salary/europe-coverage-review.json').read_text())

@pytest.mark.parametrize('country', ['GB','DE','FR','NL'])
def test_coverage_is_snapshot_union_not_measure_count_or_production(country):
    row = next(r for r in REPORT['countries'] if r['country'] == country)
    path = ROOT/'data'/row['snapshot']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['snapshot_sha256']
    snapshot = json.loads(path.read_text())
    covered = {r['occupation'] for r in snapshot['records']}
    jobs = {r['id'] for r in OCCUPATIONS}
    assert set(row['covered_occupations']) == covered
    assert set(row['missing_occupations']) == jobs - covered
    assert row['covered_count'] == len(covered)
    assert row['missing_count'] == len(jobs-covered)
    assert row['records'] == len(snapshot['records'])
    existing = next(r for r in build_report()['countries'] if r['country'] == country)
    assert {r['occupation'] for r in existing['occupations'] if r['snapshot_records']} == covered
    assert all(r['stored_observations'] == 0 for r in existing['occupations'])
    assert row['production_status'] == 'not_verified'
    assert country in COUNTRY_MAP


def test_every_gap_has_one_review_without_approved_mapping():
    with (ROOT/'docs/salary/europe-missing-occupations.csv').open() as f:
        rows = list(csv.DictReader(f))
    expected = {(r['country'], job) for r in REPORT['countries'] for job in r['missing_occupations']}
    assert {(r['country'],r['occupation']) for r in rows} == expected
    assert len(rows) == len(expected) == REPORT['total_missing_pairs'] == 63
    assert all(r['reason'] and r['evidence_url'].startswith('https://') for r in rows)
    assert all(r['new_mapping_approved'] == 'false' for r in rows)
    assert REPORT['total_covered_pairs'] == 97


def test_historical_review_is_not_new_professions_or_publication():
    cbs = REPORT['cbs_live']
    assert cbs['selected'] == sum(cbs['by_year'].values())
    assert cbs['selected'] == cbs['existing_overlaps'] + cbs['historical_candidates']
    assert cbs['existing_overlaps'] == cbs['equal_existing'] == 21
    assert cbs['historical_candidates'] == 244
    assert cbs['new_country_occupation_pairs'] == 0
    assert not cbs['publication_eligible']
    assert cbs['production_comparison'] == 'not_performed'
    assert not REPORT['production_compared']
    assert REPORT['publication_packages'] == []
    assert REPORT['new_approved_country_occupation_pairs'] == 0


def test_incomplete_downloads_have_no_integrity_claim_and_do_not_approve_gaps():
    for attempt in REPORT['source_access']:
        if attempt['status'] in ('blocked','http_error','size_limit_requires_controlled_download'):
            assert attempt['sha256'] is None and attempt['downloaded_bytes'] == 0
        elif attempt['sha256'] is not None:
            assert len(attempt['sha256']) == 64
            assert attempt['downloaded_bytes'] > 0
    assert all(r['status'] == 'blocked' for r in REPORT['source_access'] if r['country'] == 'DE')
    assert all(r['salary_equal'] and r['fte_equal'] for r in REPORT['insee_live']['existing_checks'])

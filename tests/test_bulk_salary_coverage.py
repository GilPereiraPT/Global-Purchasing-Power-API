import json
from pathlib import Path
import pytest
from app.bulk_core import BulkStore
from app.bulk_bls import observations,url
from app.bulk_coverage import build_report,html_report
from app.bulk_salary_coverage import summarize,attach,baseline_index
from tests.test_bulk_bls import release


def stage(tmp_path,status='complete'):
    z,_=release(tmp_path);p=tmp_path/'stage.sqlite3';s=BulkStore(p);checksum='a'*64
    try:
        s.artifact({'sha256':checksum,'url':url(2025),'fetched_at':'2026-10-03T00:00:00Z'})
        run=s.start('bls','2025');s.ingest('bls:2025',checksum,observations(z,2025,{}))
        s.finish(run,status,result={'acquisition_mode':'sample_test'})
    finally:s.close()
    return p


def test_bulk_coverage_and_dashboard_include_baseline_and_acquisition_modes(tmp_path):
    p=stage(tmp_path);summary=summarize([p],tmp_path)
    json.dumps(summary)
    assert summary['sources']['bls']['accepted']==12
    assert summary['sources']['bls']['acquisition_modes']==['sample_test']
    assert summary['baseline_observation_differences']==dict(new=12,revisions=0,duplicates=0)
    assert summary['newly_covered_pairs']==[dict(country='US',occupation='software_developer')]
    assert summary['production_inventory']['new'] is None
    report=attach(build_report(snapshot_dir=tmp_path),summary);html=html_report(report)
    assert 'sample_test' in html and 'not_provided' in html
    assert 'offline_bulk_sample_or_unverified' in html
    assert report['summary']['bulk_physical_salary_observations']==12


def test_latest_failed_run_excludes_provisional_observations(tmp_path):
    summary=summarize([stage(tmp_path,'failed')],tmp_path)
    assert not summary['sources'] and summary['excluded_incomplete_run_observations']==12


def test_overlapping_staging_is_not_double_counted(tmp_path):
    p=stage(tmp_path)
    with pytest.raises(ValueError):summarize([p,p],tmp_path)


def test_read_only_reporting_does_not_create_absent_database(tmp_path):
    with pytest.raises(FileNotFoundError):summarize([tmp_path/'absent.sqlite3'],tmp_path)
    assert not (tmp_path/'absent.sqlite3').exists()


def test_baseline_aliases_deduplicate_and_revisions_are_separate(tmp_path):
    fixture=Path(__file__).parent/'fixtures/bulk/bls_2025_rows.json'
    data=json.loads(fixture.read_text());row=data['rows'][0]
    from app.us_oews import IDENTITY_FIELDS,WAGE_FIELDS
    # Reconstruct the original curated snapshot layout from authentic fields.
    item={k.lower():v for k,v in row.items()};item['reference_period']='May 2025';item['published_year']=2025
    state={k.lower():v for k,v in data['rows'][1].items()};state['reference_period']='May 2025';state['published_year']=2025
    (tmp_path/'us_oews_curated.json').write_text(json.dumps({'records':[item,state]}))
    index,pairs,files=baseline_index(tmp_path)
    assert len(index)==24 and ('US','software_developer') in pairs
    p=stage(tmp_path);summary=summarize([p],tmp_path)
    assert not summary['newly_covered_pairs']
    assert summary['baseline_not_in_accepted']==12
    assert summary['baseline_observation_differences']['new']==0
    assert summary['baseline_observation_differences']['revisions']==12

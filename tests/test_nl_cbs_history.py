"""Authentic sampled observations; fixture counts are not live coverage claims."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import nl_cbs_wages as nl, earnwage_history as history, store
from app.bulk_core import BulkStore, valid_url
from app.main import app
from tests.test_portugal_benchmark_2025 import wsgi

FIXTURE = Path(__file__).parent/'fixtures/cbs_history'
ACQUIRED = '2026-10-04T13:43:35.954865+00:00'


def samples(tmp_path, monkeypatch, mutate=None):
    root = tmp_path/'sources'
    root.mkdir()
    trusted = {}
    for name, (entity, _) in nl.HISTORY_SOURCES.items():
        obj = json.loads((FIXTURE/(name+'.json')).read_text())
        if mutate:
            mutate(name, obj)
        raw = json.dumps(obj,ensure_ascii=False).encode()
        (root/('NL-'+name+'.body')).write_bytes(raw)
        trusted[name] = (entity, hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(nl, 'HISTORY_SOURCES', trusted)
    return root


def reviewed(tmp_path, monkeypatch):
    root = samples(tmp_path,monkeypatch)
    result = nl.build_history_review(root, ACQUIRED)
    monkeypatch.setattr(nl,'HISTORY_RECORDS_SHA256',result['records_sha256'])
    monkeypatch.setattr(nl,'HISTORY_REVIEW_SHA256',nl.history_review_digest(result))
    return root,result


def test_independent_real_historical_values_missing_and_status(tmp_path,monkeypatch):
    _,r = reviewed(tmp_path,monkeypatch)
    by_pair = {(v['occupation'],v['reference_period']):v for v in r['records']}
    assert by_pair['accountant','2013']['value'] == '28.8'
    assert by_pair['software_developer','2019']['value'] == '26.3'
    assert by_pair['software_developer','2025']['value'] == '34.5'
    assert by_pair['preschool_teacher','2019']['value'] == '19.3'
    assert by_pair['preschool_teacher','2024']['publication_status'] == 'definitive'
    assert by_pair['software_developer','2025']['publication_status'] == 'provisional'
    assert not any(v['occupation']=='preschool_teacher' and v['reference_period']=='2018' for v in r['records'])
    assert all(v['value'] is None for v in r['exclusions'])
    assert all(v['unit']=='EUR/hour' and v['precision']==nl.PRECISION for v in r['records'])
    assert len(nl.validate_history_review(r)) == 8


@pytest.mark.parametrize('case',['dimensions','duplicate','pagination','count','licence','version','classification','status','period','measure','nan','boolean','employee_count'])
def test_schema_metadata_and_completeness_fail_closed(tmp_path,monkeypatch,case):
    def mutate(name,obj):
        if name=='observations':
            if case=='dimensions':obj['value'][0]['Region']='NL01'
            if case=='duplicate':obj['value'].append(copy.deepcopy(obj['value'][0]))
            if case=='pagination':obj['@odata.nextLink']='https://example.org/private'
            if case=='count':obj['value'].pop()
            if case in ('nan','boolean'):
                median=next(v for v in obj['value'] if v['Measure']=='A043068')
                median['Value']=float('nan') if case=='nan' else True
            if case=='employee_count':next(v for v in obj['value'] if v['Measure']=='A045285')['Value']=None
        if name=='properties':
            if case=='duplicate':obj['ObservationCount']+=1
            if case=='licence':obj['License']='unknown'
            if case=='version':obj['Version']='202700000000'
            if case=='classification':obj['Description']='unverified classification'
        if name=='period_codes':
            if case=='status':obj['value'][-1]['Status']='Definitief'
            if case=='period':obj['value'][0]['Identifier']='2013-2014'
        if name=='measure_codes' and case=='measure':
            next(v for v in obj['value'] if v['Identifier']=='A043068')['Unit']='per year'
    with pytest.raises(ValueError):nl.build_history_review(samples(tmp_path,monkeypatch,mutate),ACQUIRED)


def test_checksum_and_symlink_protection(tmp_path,monkeypatch):
    root,_=reviewed(tmp_path,monkeypatch)
    path=root/'NL-observations.body';raw=path.read_bytes()
    path.write_bytes(raw+b' ')
    with pytest.raises(ValueError,match='checksum'):nl.build_history_review(root,ACQUIRED)
    target=tmp_path/'source.json';target.write_bytes(raw);path.unlink();path.symlink_to(target)
    with pytest.raises(ValueError,match='unsafe'):nl.build_history_review(root,ACQUIRED)


@pytest.mark.parametrize('mutation',['value','status','provenance','exclusions','license','self_rehash'])
def test_review_cannot_authenticate_its_own_modifications(tmp_path,monkeypatch,mutation):
    _,r=reviewed(tmp_path,monkeypatch)
    if mutation in ('value','self_rehash'):r['records'][0]['value']='999.00'
    if mutation=='self_rehash':r['records_sha256']=nl._records_digest(r['records'])
    if mutation=='status':r['records'][0]['publication_status']='provisional'
    if mutation=='provenance':r['provenance'][0]['salary_observation']['Value']=999
    if mutation=='exclusions':r['exclusions']=[]
    if mutation=='license':r['licence_url']='unknown'
    with pytest.raises(ValueError):nl.validate_history_review(r)


def test_staging_resume_preserves_original_identity_and_does_not_publish(tmp_path,monkeypatch):
    _,review=reviewed(tmp_path,monkeypatch)
    s=BulkStore(tmp_path/'stage.sqlite3')
    try:
        first=nl.stage_history_review(s,review)
        assert first['accepted']+first['quarantined']==8
        before=s.count()
        second=nl.stage_history_review(s,review)
        assert second['resumed_rows']==8 and second['accepted']==0 and s.count()==before
        assert not first['publication_eligible'] and not first['production_compared']
        row=json.loads(s.db.execute('SELECT payload FROM bulk_current LIMIT 1').fetchone()[0])
        assert row['unit']=='EUR/hour' and row['source_version']==nl.HISTORY_VERSION
        assert row['original']['original_period'].endswith('JJ00')
        assert row['original']['salary_observation']['ValueAttribute']=='None'
        assert row['artifact_sha256']==nl.HISTORY_SOURCES['observations'][1]
        from app.bulk_publication import projection
        with pytest.raises(ValueError):projection(row)
    finally:s.close()


def test_existing_schema_history_and_wsgi_asgi_parity(tmp_path,monkeypatch):
    _,review=reviewed(tmp_path,monkeypatch)
    path=tmp_path/'wages.sqlite3'
    monkeypatch.setattr(store,'DB_PATH',str(path))
    monkeypatch.setattr(nl,'connect',store.connect)
    monkeypatch.setattr(history,'connect',store.connect)
    nl.load_snapshot()
    with sqlite3.connect(path) as db:
        db.executemany('INSERT OR IGNORE INTO nl_cbs_wages VALUES ('+','.join('?' for _ in nl.FIELDS)+')',nl.validate_history_review(review))
    assert nl.wages('NL','software_developer')['value']==34.5
    r=history.exact_history('NL','software_developer',2018,2025)
    available={v['year']:v for v in r['observations'] if v['status']=='available'}
    assert set(available)=={2019,2025}
    assert available[2019]['reported_hourly']['value']==26.3
    assert available[2019]['reported_hourly']['precision']==nl.PRECISION
    assert available[2025]['source_observations'][0]['publication_status']=='provisional'
    assert available[2019]['annual_presentation']['status']=='unavailable'
    params=dict(country='NL',occupation='software_developer',start_year='2018',end_year='2025')
    with TestClient(app) as client:
        response=client.get('/v1/earnwage/history',params=params)
    status,body=wsgi('/v1/earnwage/history',params)
    assert response.status_code==status==200 and response.json()==body


@pytest.mark.parametrize('url',[
    'https://datasets.cbs.nl/odata/v1/CBS/00000NED',
    'https://datasets.cbs.nl/odata/v1/CBS/86355NED/../../private',
    'https://datasets.cbs.nl/odata/v1/CBS/86355NED/Unknown',
    'http://datasets.cbs.nl/odata/v1/CBS/86355NED',
])
def test_cbs_destination_is_limited_to_reviewed_dataset(url):
    with pytest.raises(ValueError):valid_url(url)


def test_offline_cli_requires_private_workspace_and_preserves_foreign_temp(tmp_path,monkeypatch):
    from scripts.nl_cbs_history import execute
    root,_=reviewed(tmp_path,monkeypatch)
    output=tmp_path/'output';output.mkdir();temporary=output/'cbs-history-review.json.tmp';temporary.write_text('user file')
    with pytest.raises(ValueError):execute(root,output,ACQUIRED)
    assert temporary.read_text()=='user file' and not (output/'staging.sqlite3').exists()
    with pytest.raises(ValueError):execute(root,Path(__file__).parent/'unsafe-output',ACQUIRED)


def test_missing_and_flagged_source_salaries_remain_excluded(tmp_path,monkeypatch):
    def mutate(name,obj):
        if name=='observations':
            median=next(v for v in obj['value'] if v['Measure']=='A043068')
            median['Value']=None
            median['ValueAttribute']='Missing'
    review=nl.build_history_review(samples(tmp_path,monkeypatch,mutate),ACQUIRED)
    excluded=next(v for v in review['exclusions'] if v['reason']=='missing_or_flagged_source_observation')
    assert excluded['value'] is None and excluded['original']['Value'] is None
    assert len(review['records'])==7
    assert not any(v['occupation']==excluded['occupation'] and v['reference_period']==excluded['period'] for v in review['records'])


def test_workspace_concurrency_and_failed_ingest_are_not_success(tmp_path,monkeypatch):
    from scripts.nl_cbs_history import execute
    from scripts.bulk_acquire import exclusive_worker
    root,review=reviewed(tmp_path,monkeypatch)
    workspace=tmp_path/'workspace';workspace.mkdir()
    with exclusive_worker(workspace):
        with pytest.raises(RuntimeError,match='Another offline worker'):
            execute(root,workspace,ACQUIRED)
    assert not (workspace/'staging.sqlite3').exists()
    s=BulkStore(tmp_path/'failed.sqlite3')
    def fail(*args,**kwargs):raise RuntimeError('isolated interruption')
    monkeypatch.setattr(s,'ingest',fail)
    try:
        with pytest.raises(RuntimeError):nl.stage_history_review(s,review)
        assert s.count()==0
        assert s.report()['runs'][-1]['status']=='failed'
    finally:s.close()


def test_real_warehouse_variation_stays_in_generic_quarantine(tmp_path,monkeypatch):
    _,review=reviewed(tmp_path,monkeypatch)
    s=BulkStore(tmp_path/'quarantine.sqlite3')
    try:
        nl.stage_history_review(s,review)
        quarantined=s.report()['quarantined_observations']
        warehouse=next(r for r in quarantined if r['occupations']==['warehouse_operator'])
        assert warehouse['period']=='2023' and warehouse['value']=='11.7'
        assert not s.db.execute("SELECT 1 FROM bulk_current WHERE json_extract(payload,'$.occupations[0]')='warehouse_operator' AND json_extract(payload,'$.period')='2023'").fetchone()
    finally:s.close()


@pytest.mark.parametrize('timestamp',['2026-10-04T13:43:35','2027-01-01T00:00:00+00:00','not a date'])
def test_original_source_timestamp_cannot_be_relabelled(tmp_path,monkeypatch,timestamp):
    root=samples(tmp_path,monkeypatch)
    with pytest.raises(ValueError):nl.build_history_review(root,timestamp)

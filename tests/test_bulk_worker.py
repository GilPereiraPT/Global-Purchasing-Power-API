import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.bulk_core import BulkStore, digest
from app.bulk_schedule import due, load
from scripts.bulk_acquire import execute, safe_workspace
from scripts.bulk_export import export
from tests.test_bulk_world_bank import payload


def test_worker_failure_reports_nonzero_and_retains_ledgers(tmp_path):
    class Failed:
        def get(self,url,ttl=0):raise OSError('DO NOT PRINT secret credentials')
    code,report=execute(tmp_path,'world_bank',['gdp_per_capita'],downloader=Failed())
    assert code==1
    assert report['runs'][0]['status']=='failed'
    text=(tmp_path/'acquisition.json').read_text()
    assert 'secret' not in text and 'OSError' in text
    assert (tmp_path/'acquisition.md').exists()


def test_worker_export_and_read_api_parity(tmp_path,monkeypatch):
    path=tmp_path/'wdi.json'
    data=payload()
    data[1][0]['indicator']['id']='FP.CPI.TOTL.ZG'
    path.write_text(json.dumps(data))
    class Fake:
        def get(self,url,ttl=0):return path,{'url':url,'sha256':digest(path)}
    workspace=tmp_path/'worker'
    code,report=execute(workspace,'world_bank',['inflation_annual'],downloader=Fake())
    assert code==0 and report['accepted_observations']==1
    code,report=execute(workspace,'world_bank',['inflation_annual'],downloader=Fake(),only_due=True)
    assert report['last_invocation'][0]['status']=='not_due'
    target=tmp_path/'api-copy.db'
    assert export(workspace/'staging.sqlite3',target)['world_bank']==1
    with sqlite3.connect(target) as db:
        from app.country_insights_store import read_indicator
        item=read_indicator(db,'PT','inflation_annual',history=True)
        assert item['value']==100 and item['year']==2024
        assert db.execute('SELECT COUNT(*) FROM bulk_artifacts').fetchone()[0]==1
    monkeypatch.setenv('EARNWAGE_INSIGHTS_DB',str(target))
    from app.main import app
    from fastapi.testclient import TestClient
    from app import native_wsgi
    client=TestClient(app)
    fast=client.get('/v1/economy/coverage')
    # Direct existing WSGI query returns the same imported observation.
    native=native_wsgi.dispatch('/v1/economy/coverage',{})
    assert fast.status_code==200 and fast.json()==native
    assert next(c for c in native['countries'] if c['country']=='PT')['indicators']['inflation_annual']['value']==100
    with pytest.raises(ValueError):export(workspace/'staging.sqlite3',target)


def test_export_refuses_incomplete_or_failed_import(tmp_path):
    staging=tmp_path/'staging.db'
    store=BulkStore(staging)
    store.start('world_bank','gdp_per_capita')
    store.close()
    with pytest.raises(ValueError):export(staging,tmp_path/'destination.db')
    assert not (tmp_path/'destination.db').exists()


def test_workspace_does_not_overlap_configured_database(tmp_path,monkeypatch):
    monkeypatch.setenv('EARNWAGE_INSIGHTS_DB',str(tmp_path/'production'/'db.sqlite'))
    with pytest.raises(ValueError):safe_workspace(tmp_path/'production')
    with pytest.raises(ValueError):safe_workspace(tmp_path)
    with pytest.raises(ValueError):safe_workspace(tmp_path/'public_html')


def test_symlinked_staging_not_followed(tmp_path):
    target=tmp_path/'existing.db'
    target.write_bytes(b'untouched')
    workspace=tmp_path/'offline';workspace.mkdir()
    (workspace/'staging.sqlite3').symlink_to(target)
    with pytest.raises(ValueError):safe_workspace(workspace)
    assert target.read_bytes()==b'untouched'


def test_non_staging_existing_database_not_modified(tmp_path):
    path=tmp_path/'application.db'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE observations(x)')
    before=path.read_bytes()
    with pytest.raises(ValueError):BulkStore(path)
    assert path.read_bytes()==before


def test_schedule_monthly_quarterly_and_failures(tmp_path):
    policy=load()
    store=BulkStore(tmp_path/'staging.db')
    assert due(store,'world_bank','gdp_per_capita',policy)
    run=store.start('world_bank','gdp_per_capita')
    store.finish(run,'complete')
    assert not due(store,'world_bank','gdp_per_capita',policy)
    assert due(store,'world_bank','gdp_per_capita',policy,datetime.now(timezone.utc)+timedelta(days=31))
    failed=store.start('world_bank','gdp_per_capita');store.finish(failed,'failed','TimeoutError')
    assert not due(store,'world_bank','gdp_per_capita',policy)
    assert policy['providers']['ecb']['check_interval_days']==1
    assert policy['providers']['ilostat']['check_interval_days']==90


@pytest.mark.parametrize('names',[[],['wrong'],['gdp_per_capita']*2,['gdp_per_capita']*5])
def test_worker_resource_limits(tmp_path,names):
    with pytest.raises(ValueError):execute(tmp_path,'world_bank',names)


def test_concurrent_workspace_worker_rejected(tmp_path):
    from scripts.bulk_acquire import exclusive_worker
    with exclusive_worker(tmp_path):
        with pytest.raises(RuntimeError):execute(tmp_path,'world_bank',['gdp_per_capita'])
    # Lock is released even after exception; no network needed.
    with exclusive_worker(tmp_path):pass


def test_acquisition_workflow_cannot_write_production_or_deploy():
    from pathlib import Path
    workflow=(Path(__file__).resolve().parent.parent/'.github/workflows/bulk-data-acquisition.yml').read_text()
    assert 'contents: read' in workflow
    assert "vars.EARNWAGE_BULK_CHECKS_ENABLED == 'true'" in workflow
    assert "github.repository == 'GilPereiraPT/Global-Purchasing-Power-API'" in workflow
    assert 'timeout-minutes: 20' in workflow
    assert 'sys.exit(code)' in workflow
    for forbidden in ('EARNWAGE_ADMIN_TOKEN','SSH','deploy_runtime','remote_data_manager','EARNWAGE_INSIGHTS_DB','GPP_CACHE_DB','pull_request:','push:'):
        assert forbidden not in workflow

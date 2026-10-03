"""All operational actions use isolated databases and private synthetic backups."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from types import SimpleNamespace
import pytest
from app import data_manager as dm, publication_control as control, bulk_publication as pub, store
from scripts import backup_earnwage_data as backup
from tests.test_data_manager import setup,request
from tests.test_bulk_publication import package,checksum


def configured(tmp_path,monkeypatch):
    token=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(backup,'ROOT',tmp_path);(tmp_path/'data').mkdir()
    monkeypatch.setattr(dm,'ROOT',tmp_path)
    monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED','true')
    dm.BACKUP_DIR.mkdir(mode=0o700)
    directory=dm.BACKUP_DIR/'bulk-packages';directory.mkdir(mode=0o700)
    p=package();sha=checksum(p);(directory/(sha+'.json')).write_bytes(pub.encode(p))
    return token,p,sha


def approve(token,sha):
    assert request('backup',token=token)[1]['status']=='available'
    assert request('recovery-test',{'confirm':'test_isolated_backup_recovery'},token=token)[1]['recovery_verified']
    assert request('bulk-preview',{'checksum':sha},token=token)[1]['status']=='review_required'


@pytest.mark.parametrize('action',['publication-conditions','recovery-test'])
@pytest.mark.parametrize('case',['missing','wrong','origin','method'])
def test_security(tmp_path,monkeypatch,action,case):
    token,_,_=configured(tmp_path,monkeypatch)
    code,_,_=request(action,token=None if case=='missing' else 'bad' if case=='wrong' else token,
                     origin='https://evil.test' if case=='origin' else None,method='GET' if case=='method' else 'POST')
    assert code=={'missing':401,'wrong':401,'origin':403,'method':405}[case]
    assert not dm._backups()


def test_real_preflight_recovery_publish_and_rollback(tmp_path,monkeypatch):
    token,p,sha=configured(tmp_path,monkeypatch)
    code,initial,_=request('publication-conditions',token=token)
    assert code==200 and not initial['ready'] and initial['free_bytes']>0
    assert initial['databases']['wages_cache']['bytes']==Path(store.DB_PATH).stat().st_size
    approve(token,sha)
    code,conditions,_=request('publication-conditions',token=token)
    assert conditions['ready'] and conditions['recovery_verified']
    assert str(tmp_path) not in json.dumps(conditions) and token not in json.dumps(conditions)
    assert not list(dm.BACKUP_DIR.glob('.recovery-*'))
    assert request('bulk-publish',{'checksum':sha,'confirm':'wrong'},token=token)[0]==409
    code,result,_=request('bulk-publish',{'checksum':sha,'confirm':'publish_reviewed_salary_package'},token=token)
    assert code==200 and result['status']=='published'
    assert not request('publication-conditions',token=token)[1]['recovery_verified']
    assert request('bulk-rollback',{'checksum':sha,'confirm':'rollback_reviewed_salary_package'},token=token)[0]==409
    assert request('recovery-test',{'confirm':'test_isolated_backup_recovery'},token=token)[0]==200
    assert request('bulk-rollback',{'checksum':sha,'confirm':'wrong'},token=token)[0]==409
    result=request('bulk-rollback',{'checksum':sha,'confirm':'rollback_reviewed_salary_package'},token=token)[1]
    assert result['status']=='rolled_back' and result['removed_rows']>0


@pytest.mark.parametrize('case',['no_backup','no_recovery','no_preview','expired_preview','expired_recovery','changed_database','changed_backup','disabled','space','permissions','conflict'])
def test_server_gates_cannot_be_bypassed(tmp_path,monkeypatch,case):
    token,p,sha=configured(tmp_path,monkeypatch)
    if case!='no_backup':request('backup',token=token)
    if case not in ('no_backup','no_recovery'):request('recovery-test',{'confirm':'test_isolated_backup_recovery'},token=token)
    if case!='no_preview':request('bulk-preview',{'checksum':sha},token=token)
    if case in ('expired_preview','expired_recovery'):
        filename='salary-review.json' if case=='expired_preview' else 'recovery-proof.json'
        f=dm.BACKUP_DIR/filename;data=json.loads(f.read_text());data['reviewed_at' if case=='expired_preview' else 'tested_at']=0;f.write_text(json.dumps(data))
    if case=='changed_database':
        with sqlite3.connect(store.DB_PATH) as db:db.execute('CREATE TABLE later(value TEXT)')
    if case=='changed_backup':
        f=dm.BACKUP_DIR/control.backup_identity(dm.BACKUP_DIR)['backup_id']/'manifest.json';f.write_text(f.read_text()+' ')
    if case=='disabled':monkeypatch.delenv('EARNWAGE_BULK_PUBLICATION_ENABLED')
    if case=='space':monkeypatch.setattr(control.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    if case=='permissions':monkeypatch.setattr(control,'_probe',lambda *_:(_ for _ in ()).throw(PermissionError()))
    if case=='conflict':
        pub.apply(store.DB_PATH,p,sha,'isolated')
        request('bulk-preview',{'checksum':sha},token=token)
        # Different checksum retains protected/duplicate target identities but no prior journal.
        p['observations'][0]['artifact_sha256']='b'*64;sha=checksum(p)
        (dm.BACKUP_DIR/'bulk-packages'/(sha+'.json')).write_bytes(pub.encode(p))
        request('bulk-preview',{'checksum':sha},token=token)
    monkeypatch.setattr(dm,'_backup',lambda *_:pytest.fail('Gate attempted fresh backup'))
    code,r,_=request('bulk-publish',{'checksum':sha,'confirm':'publish_reviewed_salary_package'},token=token)
    assert r.get('status')=='publication_disabled' if case=='disabled' else code==409


@pytest.mark.parametrize('case',['hash','incomplete','timeout','space','copy_failure'])
def test_recovery_failures_revoke_proof_and_clean(tmp_path,monkeypatch,case):
    token,p,sha=configured(tmp_path,monkeypatch);approve(token,sha)
    evidence=control.backup_identity(dm.BACKUP_DIR);folder=dm.BACKUP_DIR/evidence['backup_id']
    if case=='hash':
        f=folder/'insights.sqlite3';raw=bytearray(f.read_bytes());raw[-1]^=1;f.write_bytes(raw)
    if case=='incomplete':(folder/'wages_cache.sqlite3').unlink()
    if case=='timeout':monkeypatch.setattr(control.subprocess,'run',lambda *a,**k:(_ for _ in ()).throw(subprocess.TimeoutExpired('test',30)))
    if case=='space':monkeypatch.setattr(control.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    if case=='copy_failure':monkeypatch.setattr(control.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1))
    code,r,_=request('recovery-test',{'confirm':'test_isolated_backup_recovery'},token=token)
    assert code in (409,503) and not r.get('recovery_verified',False)
    assert not (dm.BACKUP_DIR/'recovery-proof.json').exists() and not list(dm.BACKUP_DIR.glob('.recovery-*'))


def test_clean_transaction_rejects_racing_conflicts(tmp_path):
    path=tmp_path/'wages.sqlite3'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE unrelated(value TEXT)')
    p=package();sha=checksum(p);pub.apply(path,p,sha,'first')
    before=path.read_bytes()
    with pytest.raises(ValueError,match='conflicts'):pub.apply(path,p,sha,'second',require_clean=True)
    assert path.read_bytes()==before


def test_concurrency_and_no_recovery_confirmation(tmp_path,monkeypatch):
    token,_,_=configured(tmp_path,monkeypatch)
    assert request('recovery-test',{},token=token)[0]==409
    with dm._exclusive_operation():
        assert request('recovery-test',{'confirm':'test_isolated_backup_recovery'},token=token)[0]==409

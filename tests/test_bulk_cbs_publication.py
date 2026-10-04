import copy
import hashlib
import json
import sqlite3
import pytest
from app import bulk_publication as pub, nl_cbs_wages as nl
from app.bulk_core import BulkStore
from tests.test_nl_cbs_history import reviewed


def prepared(tmp_path, monkeypatch):
    _, review = reviewed(tmp_path, monkeypatch)
    store = BulkStore(tmp_path/'staging.sqlite3')
    nl.stage_history_review(store, review)
    store.close()
    packages, _ = pub.build(tmp_path/'staging.sqlite3', cbs_review=review)
    assert len(packages) == 1
    return packages[0]


def target(tmp_path):
    path = tmp_path/'target.sqlite3'
    with sqlite3.connect(path) as db:
        nl.init(db)
        db.execute('CREATE TABLE unrelated(value TEXT)')
        db.execute("INSERT INTO unrelated VALUES ('preserved')")
    return path


def test_cbs_apply_repeat_rollback(tmp_path,monkeypatch):
    p=prepared(tmp_path,monkeypatch);db=target(tmp_path)
    count=len(p['observations'])
    assert count < len(p['cbs_review']['records'])  # staging quarantine excluded
    assert pub.preview(db,p)['inserted_rows']==count
    checksum=hashlib.sha256(pub.encode(p)).hexdigest()
    assert pub.apply(db,p,checksum,'isolated-test-backup',require_clean=True)['inserted_rows']==count
    assert pub.missing_only(db,p) is None
    assert pub.apply(db,p,checksum,'isolated-test-backup')['status']=='already_published'
    assert pub.rollback(db,checksum)['removed_rows']==count
    with sqlite3.connect(db) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert c.execute('SELECT * FROM unrelated').fetchall()==[('preserved',)]


@pytest.mark.parametrize('field', ['value','employees_thousand','publication_status','classification','source_url'])
def test_cbs_existing_metadata_protected(tmp_path,monkeypatch,field):
    p=prepared(tmp_path,monkeypatch);db=target(tmp_path)
    checksum=hashlib.sha256(pub.encode(p)).hexdigest()
    pub.apply(db,p,checksum,'isolated-test-backup')
    with sqlite3.connect(db) as c:
        c.execute('UPDATE nl_cbs_wages SET '+field+'=?', (99 if field in ('value','employees_thousand') else 'changed',))
    assert pub.preview(db,p)['protected_existing_rows']>0
    with pytest.raises(ValueError):pub.missing_only(db,p)
    with pytest.raises(ValueError):pub.rollback(db,checksum)


@pytest.mark.parametrize('mutation', ['row','review','version','provenance','without_review','held'])
def test_cbs_modified_evidence_rejected(tmp_path,monkeypatch,mutation):
    p=copy.deepcopy(prepared(tmp_path,monkeypatch))
    if mutation=='row':p['observations'][0]['value']='999'
    elif mutation=='review':
        p['cbs_review']['records'][0]['value']='999'
        p['cbs_review']['records_sha256']=nl._records_digest(p['cbs_review']['records'])
    elif mutation=='version':p['observations'][0]['source_version']='other'
    elif mutation=='provenance':p['observations'][0]['original']['period_status']='changed'
    elif mutation=='without_review':del p['cbs_review']
    else:
        from app.bulk_cbs_publication import reviewed_index
        held=next(row for row,record in reviewed_index(p['cbs_review']).values() if record['occupation']=='warehouse_operator' and record['reference_period']=='2023')
        p['observations'].append(held)
    with pytest.raises(ValueError):pub.validate(p)


def test_missing_only_keeps_new_and_preserves_duplicate(tmp_path,monkeypatch):
    p=prepared(tmp_path,monkeypatch);db=target(tmp_path)
    first={**p,'observations':p['observations'][:1]}
    pub.apply(db,first,hashlib.sha256(pub.encode(first)).hexdigest(),'isolated-test-backup')
    missing=pub.missing_only(db,p)
    assert len(missing['observations'])==len(p['observations'])-1
    assert pub.preview(db,missing)['duplicate_rows']==0


def test_offline_package_command_never_writes_model(tmp_path,monkeypatch):
    p=prepared(tmp_path,monkeypatch);db=target(tmp_path)
    review_path=tmp_path/'review.json'
    review_path.write_text(json.dumps(p['cbs_review']))
    from scripts.cbs_publication_package import prepare
    before=db.read_bytes()
    result=prepare(tmp_path/'staging.sqlite3',review_path,db,tmp_path/'packages')
    assert result['production_written'] is False
    assert len(result['packages'])==1
    assert db.read_bytes()==before
    info=result['packages'][0]
    pub.load(tmp_path/'packages'/info['file'],info['checksum'])
    with pytest.raises(FileExistsError):
        prepare(tmp_path/'staging.sqlite3',review_path,db,tmp_path/'packages')

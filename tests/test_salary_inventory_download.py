import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import time
import zipfile
import pytest
from app import data_manager as dm, native_wsgi, store
from app import salary_inventory_export as inventory, salary_inventory_download as download
from tests.test_operator_salary_inventory import source

CONFIRM = {'confirm': 'export_read_only_salary_inventory'}


def configured(tmp_path, monkeypatch):
    db = source(tmp_path)
    token = 'isolated-inventory-administrator-' + 'x' * 32
    monkeypatch.setenv('EARNWAGE_ADMIN_TOKEN', token)
    monkeypatch.setenv('GPP_CACHE_DB', str(db))
    monkeypatch.setattr(store, 'DB_PATH', str(db))
    monkeypatch.setattr(dm, 'BACKUP_DIR', tmp_path / 'private-backups')
    monkeypatch.setattr(native_wsgi, 'initialize', lambda: pytest.fail('Inventory initialized application'))
    monkeypatch.setattr(dm, 'economic_connect', lambda: pytest.fail('Inventory opened economic DB'))
    monkeypatch.setattr(dm, '_backup', lambda *a: pytest.fail('Inventory created backup'))
    return db, token


def request(token=None, payload=CONFIRM, origin=dm.ALLOW_ORIGIN, method='POST', consume=True, raw=None):
    raw = json.dumps(payload).encode() if raw is None else raw
    env = {'PATH_INFO': '/v1/admin/data-manager/salary-inventory',
        'REQUEST_METHOD': method, 'CONTENT_LENGTH': str(len(raw)),
        'wsgi.input': io.BytesIO(raw)}
    if token:env['HTTP_X_EARNWAGE_ADMIN_TOKEN'] = token
    if origin is not None:env['HTTP_ORIGIN'] = origin
    status, headers = [], []
    result = native_wsgi.application(env, lambda s,h:(status.append(s),headers.extend(h)))
    if not consume:return int(status[0].split()[0]),dict(headers),result
    try:body=b''.join(result)
    finally:
        if hasattr(result,'close'):result.close()
    return int(status[0].split()[0]),dict(headers),body


def assert_error(result, status, token, db):
    code,headers,raw=result
    assert code==status and headers['Content-Type'].startswith('application/json')
    assert token.encode() not in raw and str(db.parent).encode() not in raw
    return json.loads(raw)


def test_zip_checksums_privacy_headers_and_read_only_wal(tmp_path, monkeypatch):
    db, token = configured(tmp_path,monkeypatch)
    with sqlite3.connect(db) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('UPDATE us_oews SET a_mean=125000');writer.commit()
        before=db.read_bytes();wal=Path(str(db)+'-wal');wal_before=wal.read_bytes()
        code,headers,raw=request(token)
        assert db.read_bytes()==before and wal.read_bytes()==wal_before
    assert code==200 and headers['Content-Type']=='application/zip'
    assert int(headers['Content-Length'])==len(raw)
    assert hashlib.sha256(raw).hexdigest()==headers['X-EarnWage-Inventory-SHA256']
    assert headers['Access-Control-Allow-Origin']==dm.ALLOW_ORIGIN
    assert 'Content-Disposition' in headers['Access-Control-Expose-Headers']
    assert 'no-store' in headers['Cache-Control'] and headers['X-Content-Type-Options']=='nosniff'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={'manifest.json','us_oews.json','north_america_wages.json','ca_province_wages.json'}
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['schema']==inventory.SCHEMA and manifest['total_rows']==1
        for info in archive.infolist():
            contents=archive.read(info)
            assert token.encode() not in contents
            assert str(tmp_path).encode() not in contents and b'never-export' not in contents
            assert (info.external_attr>>16)&0o777==0o600
        for record in manifest['tables'].values():
            if record['status'] == 'absent':
                continue
            assert hashlib.sha256(archive.read(record['file'])).hexdigest()==record['sha256']
        row=json.loads(archive.read('us_oews.json'))['records'][0]
        assert row['a_mean']==125000 and row['a_median'] is None and row['reference_period']=='May 2021'
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


@pytest.mark.parametrize('auth', [None, 'wrong'])
def test_authentication_before_read_or_temporary_files(tmp_path,monkeypatch,auth):
    db,token=configured(tmp_path,monkeypatch);before=db.read_bytes()
    assert_error(request(auth),401,token,db)
    assert db.read_bytes()==before and not dm.BACKUP_DIR.exists()


def test_origin_methods_and_preflight(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch)
    assert_error(request(token,origin='https://untrusted.test'),403,token,db)
    assert_error(request(token,method='GET'),405,token,db)
    code,headers,raw=request(method='OPTIONS')
    assert code==204 and raw==b'' and 'X-EarnWage-Admin-Token' in headers['Access-Control-Allow-Headers']
    assert_error(request(method='OPTIONS',origin='https://untrusted.test'),403,token,db)
    assert not dm.BACKUP_DIR.exists()


@pytest.mark.parametrize('payload', [{}, {'confirm':'publish_reviewed_salary_package'},
    {**CONFIRM,'path':'/private/database'}, [], None])
def test_exact_confirmation_and_no_arbitrary_paths(tmp_path,monkeypatch,payload):
    db,token=configured(tmp_path,monkeypatch);before=db.read_bytes()
    assert_error(request(token,payload),422,token,db)
    assert db.read_bytes()==before
    assert not (dm.BACKUP_DIR/'salary-inventory-exports').exists()


@pytest.mark.parametrize('failure',['missing','different','symlink','public'])
def test_database_and_private_paths_fail_closed(tmp_path,monkeypatch,failure):
    db,token=configured(tmp_path,monkeypatch)
    if failure=='missing':db.unlink()
    elif failure=='different':monkeypatch.setattr(store,'DB_PATH',str(tmp_path/'different.sqlite3'))
    elif failure=='symlink':
        outside=tmp_path/'outside';outside.mkdir()
        dm.BACKUP_DIR.symlink_to(outside)
    elif failure=='public':monkeypatch.setattr(dm,'BACKUP_DIR',tmp_path/'public_html'/'exports')
    expected=409 if failure in ('missing','different') else 422
    assert_error(request(token),expected,token,db)
    if failure=='missing':assert not db.exists()
    if failure=='symlink':assert list((tmp_path/'outside').iterdir())==[]


@pytest.mark.parametrize('metadata',['token','path','filename','credentials','query'])
def test_sensitive_stored_metadata_never_returns_zip_or_logs_secrets(tmp_path,monkeypatch,caplog,metadata):
    db,token=configured(tmp_path,monkeypatch)
    field,value='occ_title',token
    if metadata=='path':value='/home3/private/server/file'
    elif metadata=='filename':field,value='source_file','/private/original.xlsx'
    elif metadata=='credentials':field,value='source_url','https://user:password@www.bls.gov/data'
    elif metadata=='query':field,value='source_url','https://www.bls.gov/data?token=private'
    with sqlite3.connect(db) as c:c.execute('UPDATE us_oews SET '+field+'=?',(value,))
    assert_error(request(token),422,token,db)
    assert token not in caplog.text and str(tmp_path) not in caplog.text and value not in caplog.text
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


@pytest.mark.parametrize('value', ['NaN', 'Infinity', float('inf')])
def test_invalid_stored_numeric_salary_refuses_entire_export(tmp_path,monkeypatch,value):
    db,token=configured(tmp_path,monkeypatch)
    with sqlite3.connect(db) as c:c.execute('UPDATE us_oews SET a_mean=?',(value,))
    assert_error(request(token),422,token,db)
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


@pytest.mark.parametrize('failure',['schema','rows','bytes','timeout','space','zip','checksum'])
def test_failures_never_send_partial_zip_and_clean_temporaries(tmp_path,monkeypatch,failure):
    db,token=configured(tmp_path,monkeypatch)
    expected=422
    if failure=='schema':
        with sqlite3.connect(db) as c:c.execute('ALTER TABLE us_oews RENAME COLUMN a_mean TO invalid')
    elif failure=='rows':monkeypatch.setattr(inventory,'MAX_ROWS',0)
    elif failure=='bytes':monkeypatch.setattr(inventory,'MAX_BYTES',1)
    elif failure=='timeout':monkeypatch.setattr(inventory,'TIMEOUT_SECONDS',0);expected=503
    elif failure=='space':
        monkeypatch.setattr(download.shutil,'disk_usage',lambda p:type('Space',(),{'free':0})());expected=503
    elif failure=='zip':
        def fail(*a,**k):raise OSError('simulated ZIP failure')
        monkeypatch.setattr(download.zipfile,'ZipFile',fail);expected=503
    elif failure=='checksum':
        original=inventory.export
        def tampered(*a,**k):
            report=original(*a,**k);(Path(a[1])/'us_oews.json').write_text('tampered');return report
        monkeypatch.setattr(inventory,'export',tampered)
    before=db.read_bytes();result=assert_error(request(token),expected,token,db)
    assert result['message'] and db.read_bytes()==before
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


def test_sqlite_lock_returns_safe_error_without_partial_export(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch);locked=sqlite3.connect(db)
    locked.execute('BEGIN EXCLUSIVE')
    try:assert assert_error(request(token),503,token,db)['error']=='inventory_database_failed'
    finally:locked.rollback();locked.close()
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


def test_interrupted_download_and_expired_download_remove_owned_files(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch)
    code,headers,result=request(token,consume=False)
    assert code==200 and result.directory.is_dir()
    assert next(result)
    result.close();assert not result.directory.exists()
    code,headers,result=request(token,consume=False)
    result.deadline=time.monotonic()-1
    with pytest.raises(TimeoutError):next(result)
    assert not result.directory.exists()


def test_retention_cleans_only_expired_reserved_directories(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch);root=dm.BACKUP_DIR/'salary-inventory-exports'
    root.mkdir(parents=True,mode=0o700);dm.BACKUP_DIR.chmod(0o700)
    old=root/'export-abcdefgh';old.mkdir();(old/'incomplete.json').write_text('{}')
    os.utime(old,(0,0))
    keep=root/'operator-backup';keep.mkdir();(keep/'keep').write_text('keep')
    outside=tmp_path/'outside';outside.mkdir();(outside/'keep').write_text('keep')
    (root/'export-abcdefgi').symlink_to(outside,target_is_directory=True)
    assert request(token)[0]==200
    assert not old.exists() and (keep/'keep').read_text()=='keep' and (outside/'keep').read_text()=='keep'


def test_pending_downloads_bounded_and_existing_manager_lock_reused(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch)
    with dm._exclusive_operation():
        assert assert_error(request(token),409,token,db)['error']=='another_import_is_running'
    root=dm.BACKUP_DIR/'salary-inventory-exports';root.mkdir(mode=0o700)
    for n in range(download.MAX_PENDING):(root/('export-aaaaaaa'+str(n))).mkdir()
    assert assert_error(request(token),409,token,db)['error']=='inventory_downloads_busy'


def test_start_response_failure_cleans_files_and_is_not_retried(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch)
    raw=json.dumps(CONFIRM).encode();calls=[]
    env={'PATH_INFO':'/v1/admin/data-manager/salary-inventory','REQUEST_METHOD':'POST',
        'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_X_EARNWAGE_ADMIN_TOKEN':token}
    def fail(status,headers):
        calls.append(status)
        raise OSError('disconnected')
    with pytest.raises(OSError):native_wsgi.application(env,fail)
    assert calls==['200 OK']
    assert list((dm.BACKUP_DIR/'salary-inventory-exports').iterdir())==[]


def test_changed_primary_key_and_private_parent_are_refused(tmp_path,monkeypatch):
    db,token=configured(tmp_path,monkeypatch)
    with sqlite3.connect(db) as c:
        c.execute('ALTER TABLE us_oews RENAME TO old_us_oews')
        c.execute('CREATE TABLE us_oews AS SELECT * FROM old_us_oews')
    assert_error(request(token),422,token,db)
    dm.BACKUP_DIR.chmod(0o755)
    assert_error(request(token),422,token,db)
    assert dm.BACKUP_DIR.stat().st_mode&0o777==0o755  # Never silently chmod existing directories.


def test_failed_immediate_cleanup_is_retried_by_orphan_retention(tmp_path,monkeypatch,caplog):
    db,token=configured(tmp_path,monkeypatch)
    code,headers,response=request(token,consume=False)
    directory=response.directory
    def fail(path,*a,**k):raise PermissionError('private cleanup failed')
    with monkeypatch.context() as context:
        context.setattr(download.shutil,'rmtree',fail)
        response.close()
    assert directory.exists() and str(directory) not in caplog.text
    os.utime(directory,(0,0))
    assert request(token)[0]==200 and not directory.exists()

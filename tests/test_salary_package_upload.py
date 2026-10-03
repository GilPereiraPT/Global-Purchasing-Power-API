"""Authenticated private upload and read-only preview through production WSGI."""
import copy
import hashlib
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from app import bulk_publication as pub, data_manager as dm, native_wsgi, store
from tests.test_data_manager import setup, request
from tests.test_bulk_publication import package


def upload(raw, token=None, checksum=None, origin=dm.ALLOW_ORIGIN, content_type='application/json', length=None):
    env={'PATH_INFO':'/v1/admin/data-manager/salary-upload','REQUEST_METHOD':'POST',
         'CONTENT_TYPE':content_type,'CONTENT_LENGTH':str(len(raw) if length is None else length),
         'wsgi.input':io.BytesIO(raw),'HTTP_ORIGIN':origin,
         'HTTP_X_EARNWAGE_PACKAGE_SHA256':checksum or hashlib.sha256(raw).hexdigest()}
    if token:env['HTTP_X_EARNWAGE_ADMIN_TOKEN']=token
    status=[]
    body=b''.join(native_wsgi.application(env,lambda s,h:status.append(s)))
    return int(status[0].split()[0]),json.loads(body)


def test_upload_and_preview_with_publication_disabled(tmp_path,monkeypatch):
    token=setup(monkeypatch,tmp_path);monkeypatch.delenv('EARNWAGE_BULK_PUBLICATION_ENABLED',raising=False)
    monkeypatch.setattr(native_wsgi,'initialize',lambda:pytest.fail('initializer ran'))
    monkeypatch.setattr(dm,'_backup',lambda *a:pytest.fail('backup/write attempted'))
    raw=pub.encode(package());checksum=hashlib.sha256(raw).hexdigest()
    before=open(store.DB_PATH,'rb').read()
    code,r=upload(raw,token);assert code==200 and r['checksum']==checksum
    saved=dm.BACKUP_DIR/'bulk-packages'/(checksum+'.json')
    assert saved.read_bytes()==raw and saved.stat().st_mode&0o077==0
    assert saved.parent.stat().st_mode&0o077==0
    code,result,_=request('bulk-preview',{'checksum':checksum},token=token)
    assert code==200 and result['inserted_rows']==r['target_rows']
    assert result['duplicate_rows']==result['protected_existing_rows']==0
    assert not result['publication_enabled'] and not result['recovery_verified']
    assert not result['publication_authorized']
    assert request('bulk-publish',{'checksum':checksum,'confirm':'publish_reviewed_salary_package'},token=token)[1]['status']=='publication_disabled'
    assert open(store.DB_PATH,'rb').read()==before


@pytest.mark.parametrize('case',['missing','wrong','origin','unconfigured'])
def test_authorization_before_reading_body(tmp_path,monkeypatch,case):
    token=setup(monkeypatch,tmp_path)
    if case=='unconfigured':monkeypatch.delenv('EARNWAGE_ADMIN_TOKEN')
    monkeypatch.setattr(dm,'_exclusive_operation',lambda:pytest.fail('unauthorized intake'))
    code,_=upload(b'not-json',None if case=='missing' else 'wrong' if case=='wrong' else token,
                  origin='https://evil.test' if case=='origin' else dm.ALLOW_ORIGIN)
    assert code=={'missing':401,'wrong':401,'origin':403,'unconfigured':503}[case]
    assert not dm.BACKUP_DIR.exists()


@pytest.mark.parametrize('case',['hash','length','truncated','empty','type','noncanonical','schema','flag','duplicate','jsonkeys','nan','utf8','conflicting_target'])
def test_invalid_upload_leaves_no_package(tmp_path,monkeypatch,case):
    token=setup(monkeypatch,tmp_path);p=package();kwargs={}
    if case=='schema':p['schema']='unknown'
    if case=='flag':p['observations'][0]['flags']='suppressed'
    if case=='duplicate':p['observations'].append(copy.deepcopy(p['observations'][0]))
    if case=='conflicting_target':
        extra=copy.deepcopy(p['observations'][0]);extra['dimensions']['extra']='unexpected';p['observations'].append(extra)
    raw=pub.encode(p)
    if case=='hash':kwargs['checksum']='a'*64
    if case=='length':kwargs['length']=pub.MAX_BYTES+1
    if case=='truncated':kwargs['length']=len(raw)+1
    if case=='empty':raw=b''
    if case=='type':kwargs['content_type']='application/zip'
    if case=='noncanonical':raw=json.dumps(p,indent=2).encode()
    if case=='jsonkeys':raw=b'{"schema":"a","schema":"b","observations":[]}'
    if case=='nan':raw=b'{"schema":NaN,"observations":[]}'
    if case=='utf8':raw=b'\xff'
    assert upload(raw,token,**kwargs)[0]==422
    directory=dm.BACKUP_DIR/'bulk-packages'
    assert not directory.exists() or list(directory.iterdir())==[]


def test_no_replacement_and_concurrent_uploads(tmp_path,monkeypatch):
    token=setup(monkeypatch,tmp_path);raw=pub.encode(package())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:upload(raw,token),range(2)))
    assert sorted(code for code,_ in results)==[200,409]
    assert upload(raw,token)[0]==409
    files=list((dm.BACKUP_DIR/'bulk-packages').iterdir());assert len(files)==1 and files[0].read_bytes()==raw


@pytest.mark.parametrize('case',['symlink','public','permissions','space','quota','io'])
def test_storage_security_and_failures(tmp_path,monkeypatch,case):
    from app import salary_package_upload as intake
    token=setup(monkeypatch,tmp_path);raw=pub.encode(package())
    if case=='public':monkeypatch.setattr(dm,'BACKUP_DIR',tmp_path/'public_html'/'backups')
    if case=='symlink':
        target=tmp_path/'other';target.mkdir();dm.BACKUP_DIR.symlink_to(target,target_is_directory=True)
    if case=='permissions':
        dm.BACKUP_DIR.mkdir();dm.BACKUP_DIR.chmod(0o755)
    if case=='space':monkeypatch.setattr(intake.shutil,'disk_usage',lambda _:type('Usage',(),{'free':0})())
    if case=='quota':monkeypatch.setattr(intake,'MAX_PACKAGES',0)
    if case=='io':monkeypatch.setattr(intake.os,'link',lambda *a:(_ for _ in ()).throw(PermissionError()))
    assert upload(raw,token)[0] in (409,422,503)
    directory=dm.BACKUP_DIR/'bulk-packages'
    assert not directory.exists() or list(directory.iterdir())==[]


def test_upload_route_preflight_and_no_get(tmp_path,monkeypatch):
    token=setup(monkeypatch,tmp_path)
    assert request('salary-upload',token=token,method='GET')[0]==405
    code,_,headers=request('salary-upload',origin=dm.ALLOW_ORIGIN,method='OPTIONS')
    assert code==204 and 'X-EarnWage-Package-SHA256' in headers['Access-Control-Allow-Headers']


@pytest.mark.parametrize('enabled',[None,'false','TRUE','1',''])
def test_preview_never_enables_publication(tmp_path,monkeypatch,enabled):
    token=setup(monkeypatch,tmp_path)
    if enabled is None:monkeypatch.delenv('EARNWAGE_BULK_PUBLICATION_ENABLED',raising=False)
    else:monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED',enabled)
    raw=pub.encode(package());sha=hashlib.sha256(raw).hexdigest()
    assert upload(raw,token)[0]==200
    result=request('bulk-preview',{'checksum':sha},token=token)[1]
    assert result['status']=='review_required' and not result['publication_enabled']
    assert os.environ.get('EARNWAGE_BULK_PUBLICATION_ENABLED')==enabled


def test_existing_target_symlink_and_interruption_never_replace(tmp_path,monkeypatch):
    token=setup(monkeypatch,tmp_path);raw=pub.encode(package());sha=hashlib.sha256(raw).hexdigest()
    dm.BACKUP_DIR.mkdir(mode=0o700)
    directory=dm.BACKUP_DIR/'bulk-packages';directory.mkdir(mode=0o700)
    victim=tmp_path/'keep';victim.write_bytes(b'original');target=directory/(sha+'.json');target.symlink_to(victim)
    assert upload(raw,token)[0]==409 and victim.read_bytes()==b'original'
    target.unlink()
    from app import salary_package_upload as intake
    monkeypatch.setattr(intake.os,'fsync',lambda *a:(_ for _ in ()).throw(OSError('interrupted')))
    assert upload(raw,token)[0]==503 and list(directory.iterdir())==[]

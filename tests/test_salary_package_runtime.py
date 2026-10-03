"""Test archive built by the actual production workflow, without a server."""
import os
import subprocess
import sys
from pathlib import Path
from scripts import deploy_runtime as runtime
from tests.test_deployment_recovery import package
from tests.test_bulk_publication import package as salary_package
from app.bulk_publication import encode


def test_packaged_wsgi_salary_upload_preview(package,tmp_path):
    root=tmp_path/'passenger';root.mkdir();runtime.install(root,package)
    members,_=runtime.read_archive(package)
    assert 'app/salary_package_upload.py' in members
    assert not any('docs/' in n or 'bulk-packages/' in n or n.endswith(('.zip','.sqlite3','.env')) for n in members)
    source=tmp_path/'package.json';source.write_bytes(encode(salary_package()))
    script=r'''
import hashlib,io,json,os,sqlite3,sys
from pathlib import Path
from passenger_wsgi import application
from app import native_wsgi,data_manager as dm
native_wsgi.initialize=lambda: (_ for _ in ()).throw(AssertionError('initializer ran'))
dm._backup=lambda *a: (_ for _ in ()).throw(AssertionError('backup ran'))
db=Path(os.environ['GPP_CACHE_DB'])
with sqlite3.connect(db) as c:c.execute('CREATE TABLE unrelated(value TEXT)')
before=db.read_bytes();raw=Path(sys.argv[1]).read_bytes();sha=hashlib.sha256(raw).hexdigest()
def call(action,body,token=True):
 env={'PATH_INFO':'/v1/admin/data-manager/'+action,'REQUEST_METHOD':'POST',
      'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),
      'wsgi.input':io.BytesIO(body),'HTTP_ORIGIN':dm.ALLOW_ORIGIN,
      'HTTP_X_EARNWAGE_PACKAGE_SHA256':sha}
 if token:env['HTTP_X_EARNWAGE_ADMIN_TOKEN']=os.environ['EARNWAGE_ADMIN_TOKEN']
 status=[];reply=b''.join(application(env,lambda s,h:status.append(s)))
 return int(status[0].split()[0]),json.loads(reply)
assert call('salary-upload',raw,False)[0]==401
code,result=call('salary-upload',raw);assert code==200 and result['checksum']==sha
assert call('salary-upload',raw)[0]==409
code,preview=call('bulk-preview',json.dumps({'checksum':sha}).encode())
assert code==200 and preview['inserted_rows']==result['target_rows'] and not preview['publication_enabled']
assert preview['duplicate_rows']==preview['protected_existing_rows']==0
assert not preview['recovery_verified']
assert call('bulk-publish',json.dumps({'checksum':sha,'confirm':'publish_reviewed_salary_package'}).encode())[1]['status']=='publication_disabled'
assert db.read_bytes()==before
assert not Path(os.environ['EARNWAGE_INSIGHTS_DB']).exists()
assert 'fastapi' not in sys.modules
print('packaged upload and preview verified')
'''
    env={**os.environ,'GPP_CACHE_DB':str(tmp_path/'wages.sqlite3'),
         'EARNWAGE_INSIGHTS_DB':str(tmp_path/'never-created.sqlite3'),
         'EARNWAGE_ADMIN_TOKEN':'isolated-package-test-'+'x'*32}
    env.pop('EARNWAGE_BULK_PUBLICATION_ENABLED',None)
    result=subprocess.run([sys.executable,'-c',script,str(source)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr

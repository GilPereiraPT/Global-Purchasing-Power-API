"""Exercise the actual deployment workflow archive in an isolated Passenger root."""
import os
import subprocess
import sys
from pathlib import Path
from scripts import deploy_runtime as runtime
from tests.test_deployment_recovery import package
from tests.test_operator_salary_inventory import source


def test_actual_packaged_wsgi_inventory_export(package,tmp_path):
    db=source(tmp_path)
    root=tmp_path/'passenger';root.mkdir();runtime.install(root,package)
    members,_=runtime.read_archive(package)
    assert {'app/salary_inventory_export.py','app/salary_inventory_download.py'}<=members.keys()
    assert not any('docs/' in n or n.endswith(('.zip','.sqlite3','.env')) for n in members)
    script=r'''
import io,json,hashlib,sqlite3,zipfile,os,sys
from pathlib import Path
from passenger_wsgi import application
from app import native_wsgi,data_manager as dm
native_wsgi.initialize=lambda: (_ for _ in ()).throw(AssertionError('application initialized'))
dm.economic_connect=lambda: (_ for _ in ()).throw(AssertionError('economic DB opened'))
dm._backup=lambda *a: (_ for _ in ()).throw(AssertionError('backup executed'))
root=Path.cwd();db=Path(os.environ['GPP_CACHE_DB']);before=db.read_bytes()
body=json.dumps({'confirm':'export_read_only_salary_inventory'}).encode()
def request(token):
 status=[];headers=[]
 env={'PATH_INFO':'/v1/admin/data-manager/salary-inventory','REQUEST_METHOD':'POST',
      'CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body),'HTTP_ORIGIN':dm.ALLOW_ORIGIN}
 if token:env['HTTP_X_EARNWAGE_ADMIN_TOKEN']=token
 result=application(env,lambda s,h:(status.append(s),headers.extend(h)))
 try:raw=b''.join(result)
 finally:
  if hasattr(result,'close'):result.close()
 return status[0],dict(headers),raw
assert request(None)[0]=='401 Unauthorized'
status,headers,raw=request(os.environ['EARNWAGE_ADMIN_TOKEN'])
assert status=='200 OK' and headers['Content-Type']=='application/zip'
assert len(raw)==int(headers['Content-Length'])
assert hashlib.sha256(raw).hexdigest()==headers['X-EarnWage-Inventory-SHA256']
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 manifest=json.loads(z.read('manifest.json'))
 assert manifest['total_rows']==1
 for record in manifest['tables'].values():
  if record['status']=='absent':continue
  contents=z.read(record['file'])
  assert hashlib.sha256(contents).hexdigest()==record['sha256']
  assert os.environ['EARNWAGE_ADMIN_TOKEN'].encode() not in contents
  assert str(db.parent).encode() not in contents
assert db.read_bytes()==before
assert list((root/'_earnwage_backups/salary-inventory-exports').iterdir())==[]
assert not Path(os.environ['EARNWAGE_INSIGHTS_DB']).exists()
assert 'fastapi' not in sys.modules and 'a2wsgi' not in sys.modules
print('packaged native WSGI inventory export verified')
'''
    env={**os.environ,'GPP_CACHE_DB':str(db),
        'EARNWAGE_INSIGHTS_DB':str(tmp_path/'must-not-create-insights.sqlite3'),
        'EARNWAGE_ADMIN_TOKEN':'isolated-packaged-inventory-token-'+'x'*32}
    result=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,
        capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr
    assert 'packaged native WSGI inventory export verified' in result.stdout

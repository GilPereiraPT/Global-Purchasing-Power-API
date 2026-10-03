"""End-to-end native Passenger entry from the actual deployment archive.

Synthetic protocol scenario; genuine production data is never used. Existing
committed snapshots provide realistic baseline schemas and API responses.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from app.bulk_core import BulkStore
from app.bulk_bls import observations,url
from tests.test_bulk_bls import release
from tests.test_deployment_recovery import package
from scripts import deploy_runtime as runtime


def test_packaged_wsgi_complete_publication_sequence(package,tmp_path):
 archive,_=release(tmp_path);rows=list(observations(archive,2025,{}))
 for r in rows:r.update(period='2024',original_period='May 2024',source_url=url(2024),source_member='oesm24all/all_data_M_2024.xlsx')
 staging=tmp_path/'stage.sqlite3';s=BulkStore(staging)
 sha=hashlib.sha256(archive.read_bytes()).hexdigest()
 try:
  s.artifact({'url':url(2024),'sha256':sha});run=s.start('bls','2024')
  s.ingest('synthetic-protocol',sha,rows);s.finish(run,'complete',result={'acquisition_mode':'sample_test'})
 finally:s.close()
 root=tmp_path/'passenger';root.mkdir();runtime.install(root,package)
 contents,_=runtime.read_archive(package)
 assert {'app/bulk_publication.py','app/bulk_core.py','app/bulk_classifications.py',
         'scripts/bulk_publication_package.py','scripts/backup_earnwage_data.py',
         'scripts/restore_earnwage_data.py','data/job_bank_2025_geographies.json'}<=contents.keys()
 assert not any('generated' in name or name.endswith(('.sqlite3','.env','.zip','.xlsx')) for name in contents)
 script=r'''
import io,json,os,sqlite3,sys
from pathlib import Path
import httpx
httpx.get=lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected network'))
from passenger_wsgi import application
assert 'fastapi' not in sys.modules and 'a2wsgi' not in sys.modules
from app import data_manager as dm
from app.country_insights_store import connect
from scripts.bulk_publication_package import export
from scripts.restore_earnwage_data import restore
root=Path.cwd();staging=Path(sys.argv[1]);dm.BACKUP_DIR=root/'_earnwage_backups'
with connect() as db:
 db.execute("INSERT INTO observations VALUES ('PT','life_expectancy',2024,82.1,'test')");db.commit()
def request(path,payload=None):
 raw=json.dumps(payload or {}).encode();status=[]
 env={'PATH_INFO':path,'REQUEST_METHOD':'GET' if payload is None else 'POST','QUERY_STRING':'',
      'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
      'HTTP_X_EARNWAGE_ADMIN_TOKEN':os.environ['EARNWAGE_ADMIN_TOKEN']}
 result=json.loads(b''.join(application(env,lambda s,h:status.append(s))))
 assert status[0].startswith('200'),(status,result)
 return result
paths=['/v1/health','/v1/countries','/v1/occupations','/v1/wages/US/software_developer',
       '/v1/wages/CA/nurse','/v1/ca/provinces/nurse/ON']
before={p:request(p) for p in paths}
index=export(staging,dm.BACKUP_DIR/'bulk-packages')
assert len(index['packages'])==1
sha=index['packages'][0]['checksum'];prefix='/v1/admin/data-manager/'
assert request(prefix+'bulk-preview',{'checksum':sha})['inserted_rows']==1
published=request(prefix+'bulk-publish',{'checksum':sha,'confirm':'publish_reviewed_salary_package'})
assert published['status']=='published'
assert request(prefix+'bulk-publish',{'checksum':sha,'confirm':'publish_reviewed_salary_package'})['status']=='already_published'
from app import native_wsgi
native_wsgi.INITIALIZED=False
assert {p:request(p) for p in paths}==before
with sqlite3.connect(os.environ['GPP_CACHE_DB']) as db:
 assert db.execute("SELECT count(*) FROM us_oews WHERE published_year=2024").fetchone()[0]==1
assert request(prefix+'bulk-rollback',{'checksum':sha,'confirm':'rollback_reviewed_salary_package'})['removed_rows']==1
recovered=restore(dm.BACKUP_DIR/published['backup_id'],root/'recovered')
with sqlite3.connect(recovered/'wages_cache.sqlite3') as db:
 assert db.execute("SELECT count(*) FROM us_oews WHERE published_year=2024").fetchone()[0]==0
with sqlite3.connect(recovered/'insights.sqlite3') as db:
 assert db.execute("SELECT value FROM observations WHERE country='PT'").fetchone()[0]==82.1
assert {p:request(p) for p in paths}==before
print('native WSGI sequence, restart, baseline API and restoration: ok')
'''
 env={**os.environ,'GPP_CACHE_DB':str(root/'wages.sqlite3'),
      'EARNWAGE_INSIGHTS_DB':str(root/'insights.sqlite3'),
      'EARNWAGE_ADMIN_TOKEN':'isolated-runtime-test-token-xxxxxxxxxxxxxxxx',
      'EARNWAGE_BULK_PUBLICATION_ENABLED':'true'}
 result=subprocess.run([sys.executable,'-c',script,str(staging)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
 assert result.returncode==0,result.stderr
 assert 'native WSGI sequence' in result.stdout

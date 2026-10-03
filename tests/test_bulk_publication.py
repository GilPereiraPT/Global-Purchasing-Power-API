import copy
import hashlib
import json
import sqlite3
from pathlib import Path
import pytest
from app import bulk_publication as pub
from app import data_manager as dm, store
from tests.test_data_manager import request,setup


def source_rows():
    from app.bulk_job_bank import observations
    rows=list(observations(Path('tests/fixtures/bulk/job_bank_2025.csv'),{}))
    for row in rows:row['artifact_sha256']='a'*64
    return [r for r in rows if r['value'] is not None and not r['geography'].startswith('CA:economic_region:') and (r['geography']!='national' or r['measure'] in ('median','mean'))]


def package():return {'schema':pub.SCHEMA,'observations':source_rows()}

def checksum(p):return hashlib.sha256(pub.encode(p)).hexdigest()


@pytest.mark.parametrize('action', ['bulk-publish', 'bulk-rollback'])
@pytest.mark.parametrize('enabled', [None, 'false', 'TRUE', '1', ''])
def test_every_bulk_action_requires_exact_explicit_activation(tmp_path, monkeypatch, action, enabled):
 secret=setup(monkeypatch,tmp_path)
 if enabled is None:monkeypatch.delenv('EARNWAGE_BULK_PUBLICATION_ENABLED',raising=False)
 else:monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED',enabled)
 monkeypatch.setattr(dm,'_backup',lambda *a:pytest.fail('disabled action attempted a backup'))
 assert request(action,token=secret)[:2]==(200,{'status':'publication_disabled'})
 with sqlite3.connect(store.DB_PATH) as db:
  assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0


@pytest.mark.parametrize('action', ['bulk-preview', 'bulk-publish', 'bulk-rollback'])
def test_enabled_bulk_actions_still_require_admin_authentication(tmp_path, monkeypatch, action):
 setup(monkeypatch,tmp_path)
 monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED','true')
 monkeypatch.setattr(dm,'_bulk_publication',lambda *a:pytest.fail('unauthenticated action reached publication'))
 assert request(action,token=None)[0]==401

def database(tmp_path):
 p=tmp_path/'wages.sqlite3'
 with sqlite3.connect(p) as db:db.execute('CREATE TABLE unrelated (value TEXT)');db.execute("INSERT INTO unrelated VALUES ('keep')")
 return p


def test_publish_idempotence_and_guarded_rollback(tmp_path):
 p=package();db=database(tmp_path);digest=checksum(p)
 assert pub.preview(db,p)['inserted_rows']>0
 r=pub.apply(db,p,digest,'backup-test');assert r['status']=='published'
 assert pub.apply(db,p,digest,'backup-test')['status']=='already_published'
 assert pub.preview(db,p)['duplicate_rows']==r['inserted_rows']
 assert pub.rollback(db,digest)['removed_rows']==r['inserted_rows']
 assert pub.rollback(db,digest)['status']=='already_rolled_back'
 with sqlite3.connect(db) as c:assert c.execute('select value from unrelated').fetchone()[0]=='keep'


def test_never_overwrite_existing_or_duplicate_on_changed_package(tmp_path):
 db=database(tmp_path);p=package();digest=checksum(p);pub.apply(db,p,digest,'backup-test')
 changed=copy.deepcopy(p);changed['observations'][0]['value']='999'
 assert pub.preview(db,changed)['protected_existing_rows']==1
 before=sqlite3.connect(db).execute('select sum(value) from north_america_wages').fetchone()[0]
 pub.apply(db,changed,checksum(changed),'backup-test')
 assert sqlite3.connect(db).execute('select sum(value) from north_america_wages').fetchone()[0]==before
 assert pub.rollback(db,checksum(changed))['removed_rows']==0


def test_rollback_refuses_later_edits_and_keeps_all_rows(tmp_path):
 db=database(tmp_path);p=package();digest=checksum(p);pub.apply(db,p,digest,'backup-test')
 with sqlite3.connect(db) as c:c.execute('update north_america_wages set value=777')
 with pytest.raises(ValueError,match='changed'):pub.rollback(db,digest)
 assert sqlite3.connect(db).execute('select count(*) from ca_province_wages').fetchone()[0]>0

@pytest.mark.parametrize('change', ['checksum','source','geography','classification','flag','duplicate','nonfinite','licence','limit'])
def test_reject_invalid_packages(tmp_path,change):
 p=package();r=p['observations'][0]
 if change=='checksum':r['artifact_sha256']='bad'
 elif change=='source':r['source_url']='https://evil.test/file'
 elif change=='geography':r['original_geography']='ER3510'
 elif change=='classification':r['classification']='NOC2021:00000'
 elif change=='flag':r['flags']='unavailable'
 elif change=='duplicate':p['observations'].append(copy.deepcopy(r))
 elif change=='nonfinite':r['value']='NaN'
 elif change=='licence':r['licence_url']='unknown'
 elif change=='limit':p['observations']*=200
 with pytest.raises((ValueError,ArithmeticError)):pub.validate(p)


def test_bad_checksum_symlinks_database_budget_and_incompatible_schema(tmp_path):
 p=package();raw=pub.encode(p);file=tmp_path/'package.json';file.write_bytes(raw)
 with pytest.raises(ValueError,match='checksum'):pub.load(file,'b'*64)
 assert pub.load(file,checksum(p))==p
 link=tmp_path/'link.json';link.symlink_to(file)
 with pytest.raises(ValueError):pub.load(link,checksum(p))
 db=database(tmp_path)
 with sqlite3.connect(db) as c:c.execute('CREATE TABLE north_america_wages (value REAL)')
 with pytest.raises(ValueError,match='schema'):pub.apply(db,p,checksum(p),'backup-test')
 assert sqlite3.connect(db).execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0
 big=tmp_path/'big.sqlite3'
 with big.open('wb') as f:f.truncate(pub.MAX_DATABASE_BYTES+1)
 with pytest.raises(ValueError,match='budget'):pub.preview(big,p)


def test_data_manager_auth_confirmation_fresh_backup_and_restore(tmp_path,monkeypatch):
 secret=setup(monkeypatch,tmp_path)
 from scripts import backup_earnwage_data as backup
 from scripts.restore_earnwage_data import restore
 monkeypatch.setattr(backup,'ROOT',tmp_path);(tmp_path/'data').mkdir()
 assert request('bulk-publish',token=None)[0]==401
 assert request('bulk-publish',token=secret)[1]['status']=='publication_disabled'
 monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED','true')
 p=package();digest=checksum(p);directory=dm.BACKUP_DIR/'bulk-packages';directory.mkdir(parents=True)
 (directory/(digest+'.json')).write_bytes(pub.encode(p))
 payload={'checksum':digest}
 assert request('bulk-preview',payload,token=secret)[1]['status']=='review_required'
 assert request('bulk-publish',payload,token=secret)[0]==422
 code,result,_=request('bulk-publish',{**payload,'confirm':'publish_reviewed_salary_package'},token=secret)
 assert code==200 and result['status']=='published'
 recovered=restore(dm.BACKUP_DIR/result['backup_id'],tmp_path/'recovered')
 with sqlite3.connect(recovered/'wages_cache.sqlite3') as c:assert c.execute("SELECT count(*) FROM sqlite_master WHERE name='north_america_wages'").fetchone()[0]==0
 assert request('bulk-rollback',{**payload,'confirm':'rollback_reviewed_salary_package'},token=secret)[1]['status']=='rolled_back'
 assert store.DB_PATH==str(tmp_path/'real_wages.sqlite3')


def test_backup_failure_cannot_write(tmp_path,monkeypatch):
 secret=setup(monkeypatch,tmp_path);monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED','true')
 p=package();digest=checksum(p);directory=dm.BACKUP_DIR/'bulk-packages';directory.mkdir(parents=True);(directory/(digest+'.json')).write_bytes(pub.encode(p))
 monkeypatch.setattr(dm,'_backup',lambda _: (_ for _ in ()).throw(OSError('failure')))
 assert request('bulk-publish',{'checksum':digest,'confirm':'publish_reviewed_salary_package'},token=secret)[0]==503
 with sqlite3.connect(store.DB_PATH) as c:assert c.execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0


def test_bls_projection_preserves_measures_nulls_and_protects_existing_row(tmp_path):
 from tests.test_bulk_bls import release
 from app.bulk_bls import observations
 archive,_=release(tmp_path,[{'H_MEDIAN':'#'}])
 rows=[r for r in observations(archive,2025,{}) if r['value'] is not None]
 for r in rows:r['artifact_sha256']='a'*64
 p={'schema':pub.SCHEMA,'observations':rows};db=database(tmp_path)
 assert pub.apply(db,p,checksum(p),'backup-test')['inserted_rows']==1
 with sqlite3.connect(db) as c:
  r=c.execute('select h_mean,h_median,a_mean,reference_period,source_url from us_oews').fetchone()
 assert r[:4]==(100,None,200000,'May 2025')
 # A new accepted measure must not overwrite or complete an existing source row.
 changed=copy.deepcopy(p);changed['observations'][0]['value']='101';changed['observations'][0]['original_salary_token']='101'
 assert pub.apply(db,changed,checksum(changed),'backup-test')['protected_existing_rows']==1
 assert sqlite3.connect(db).execute('select count(*) from us_oews').fetchone()[0]==1


def test_build_acceptance_limits_and_no_split_oews_target_rows(tmp_path):
 from tests.test_bulk_salary_coverage import stage
 from scripts.bulk_publication_package import export
 path=stage(tmp_path)
 packages,excluded=pub.build(path,12)
 assert len(packages)==1 and len(packages[0]['observations'])==12
 with pytest.raises(ValueError,match='Target row'):pub.build(path,11)
 output=tmp_path/'out';manifest=export(path,output,12)
 assert manifest['packages'][0]['bytes']<pub.MAX_BYTES
 pub.load(output/manifest['packages'][0]['file'],manifest['packages'][0]['checksum'])
 with pytest.raises(ValueError):export(path,output)
 with sqlite3.connect(path) as c:c.execute("UPDATE bulk_runs SET status='failed'")
 with pytest.raises(ValueError,match='Incomplete'):pub.build(path)


def test_build_excludes_missing_and_quarantine(tmp_path):
 from tests.test_bulk_salary_coverage import stage
 path=stage(tmp_path)
 with sqlite3.connect(path) as c:
  key=c.execute('select key from bulk_current limit 1').fetchone()[0]
  c.execute("UPDATE bulk_versions SET status='quarantined' WHERE key=?",(key,))
 with pytest.raises(ValueError,match='status mismatch'):pub.build(path)


def test_transaction_failure_rolls_back_entire_package(tmp_path):
 from app.ca_province_wages import init
 db=database(tmp_path)
 with sqlite3.connect(db) as c:
  init(c);c.execute("CREATE TRIGGER block_import BEFORE INSERT ON ca_province_wages BEGIN SELECT RAISE(ABORT,'test failure'); END")
 p=package()
 with pytest.raises(sqlite3.Error):pub.apply(db,p,checksum(p),'backup-test')
 with sqlite3.connect(db) as c:
  assert c.execute('select count(*) from ca_province_wages').fetchone()[0]==0
  assert c.execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0

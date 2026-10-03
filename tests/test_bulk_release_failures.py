"""Operational failure tests use only explicit tmp_path databases and test tokens."""
import errno
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace
import pytest
from app import bulk_publication as pub, data_manager as dm, store
from scripts import backup_earnwage_data as backup
from tests.test_bulk_publication import package,checksum,database
from tests.test_data_manager import setup,request


def configured(monkeypatch,tmp_path):
 secret=setup(monkeypatch,tmp_path)
 monkeypatch.setenv('EARNWAGE_BULK_PUBLICATION_ENABLED','true')
 monkeypatch.setattr(backup,'ROOT',tmp_path);(tmp_path/'data').mkdir()
 p=package();sha=checksum(p);dm.BACKUP_DIR.mkdir(mode=0o700);directory=dm.BACKUP_DIR/'bulk-packages';directory.mkdir(mode=0o700)
 (directory/(sha+'.json')).write_bytes(pub.encode(p))
 return secret,p,{'checksum':sha,'confirm':'publish_reviewed_salary_package'}


def test_insufficient_space_refuses_before_backup_or_publication(monkeypatch,tmp_path):
 secret,p,payload=configured(monkeypatch,tmp_path)
 monkeypatch.setattr(backup.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
 code,r,_=request('bulk-publish',payload,token=secret)
 assert code==409 and r['error']=='publication_review_required'
 assert dm._backups()==[]
 with sqlite3.connect(store.DB_PATH) as db:assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0


@pytest.mark.parametrize('variable',['GPP_CACHE_DB','EARNWAGE_INSIGHTS_DB'])
def test_missing_database_never_recreated(monkeypatch,tmp_path,variable):
 secret,p,payload=configured(monkeypatch,tmp_path)
 path=Path(os.environ[variable]);path.unlink()
 code,r,_=request('bulk-publish',payload,token=secret)
 assert code==409 and r['status']=='prerequisites_missing'
 assert not path.exists() and not dm._backups()


def test_disk_exhaustion_during_copy_removes_incomplete_backup(monkeypatch,tmp_path):
 secret,p,payload=configured(monkeypatch,tmp_path)
 from tests.test_publication_control import approve
 approve(secret,payload['checksum'])
 existing=set(dm.BACKUP_DIR.glob('backup-*'))
 (tmp_path/'data'/'test.json').write_text('{}')
 before=Path(store.DB_PATH).read_bytes()
 monkeypatch.setattr(backup.shutil,'copy2',lambda *args: (_ for _ in ()).throw(OSError(errno.ENOSPC,'disk full')))
 assert request('bulk-publish',payload,token=secret)[0]==503
 assert set(dm.BACKUP_DIR.glob('backup-*'))==existing
 assert Path(store.DB_PATH).read_bytes()==before


def test_exclusive_manager_lock_rejects_second_request(monkeypatch,tmp_path):
 secret,p,payload=configured(monkeypatch,tmp_path)
 with dm._exclusive_operation():
  code,r,_=request('bulk-publish',payload,token=secret)
 assert code==409 and r['error']=='another_import_is_running'
 assert not dm._backups()


def test_busy_backup_has_deadline_and_preserves_sources(monkeypatch,tmp_path):
 configured(monkeypatch,tmp_path)
 monkeypatch.setattr(backup,'BACKUP_TIMEOUT_SECONDS',0.15)
 locked=sqlite3.connect(os.environ['GPP_CACHE_DB']);locked.execute('BEGIN EXCLUSIVE')
 destination=tmp_path/'attempt';started=time.monotonic()
 try:
  with pytest.raises(RuntimeError,match='backup_timeout'):backup.backup(str(destination))
 finally:locked.rollback();locked.close()
 assert time.monotonic()-started<2 and not destination.exists()
 assert Path(os.environ['EARNWAGE_INSIGHTS_DB']).is_file()


def test_wal_writer_lock_fails_bounded_without_partial_publication(tmp_path):
 db=database(tmp_path);p=package()
 locked=sqlite3.connect(db);locked.execute('PRAGMA journal_mode=WAL');locked.execute('BEGIN IMMEDIATE')
 started=time.monotonic()
 try:
  with pytest.raises(sqlite3.OperationalError,match='locked'):pub.apply(db,p,checksum(p),'isolated-backup')
 finally:locked.rollback();locked.close()
 assert 4<=time.monotonic()-started<8
 with sqlite3.connect(db) as c:assert c.execute("SELECT count(*) FROM sqlite_master WHERE name='bulk_publications'").fetchone()[0]==0


def test_actual_sqlite_full_rolls_back_whole_transaction(tmp_path,monkeypatch):
 db=database(tmp_path);p=package();original=pub._connect
 def limited(path,readonly=False):
  c=original(path,readonly)
  pages=c.execute('PRAGMA page_count').fetchone()[0];c.execute('PRAGMA max_page_count='+str(pages))
  return c
 monkeypatch.setattr(pub,'_connect',limited)
 with pytest.raises(sqlite3.OperationalError,match='full'):pub.apply(db,p,checksum(p),'isolated-backup')
 with sqlite3.connect(db) as c:
  assert c.execute('select value from unrelated').fetchone()[0]=='keep'
  assert c.execute("select count(*) from sqlite_master where name='bulk_publications'").fetchone()[0]==0


def test_keyboard_interrupt_during_backup_cleans_only_new_destination(monkeypatch,tmp_path):
 configured(monkeypatch,tmp_path)
 existing=tmp_path/'existing';existing.mkdir();(existing/'keep').write_text('existing backup')
 monkeypatch.setattr(backup,'digest',lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
 with pytest.raises(KeyboardInterrupt):backup.backup(str(tmp_path/'interrupted'))
 assert not (tmp_path/'interrupted').exists() and (existing/'keep').read_text()=='existing backup'


def test_sigkill_during_insert_recovers_sqlite_transaction(tmp_path):
 db=database(tmp_path);p=package();payload=tmp_path/'package.json';payload.write_bytes(pub.encode(p));marker=tmp_path/'in-transaction'
 code='''
import json,sys,time
from pathlib import Path
from app import bulk_publication as pub
from app.ca_province_wages import init
path,payload,marker=sys.argv[1:]
original=pub._connect
c=original(path);init(c);c.commit();c.close()
def paused(path,readonly=False):
 c=original(path,readonly)
 def stop():
  Path(marker).write_text('transaction active')
  time.sleep(30)
  return 0
 c.create_function('pause_test',0,stop)
 c.execute("CREATE TEMP TRIGGER pause_insert BEFORE INSERT ON ca_province_wages BEGIN SELECT pause_test(); END")
 return c
pub._connect=paused
p=json.loads(Path(payload).read_text())
import hashlib
pub.apply(path,p,hashlib.sha256(pub.encode(p)).hexdigest(),'isolated-backup')
'''
 proc=subprocess.Popen([sys.executable,'-c',code,str(db),str(payload),str(marker)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  deadline=time.monotonic()+5
  while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.01)
  assert marker.exists(),proc.stderr.read() if proc.poll() is not None else 'child did not enter transaction'
  proc.kill();proc.wait(timeout=5)
 finally:
  if proc.poll() is None:proc.kill();proc.wait(timeout=5)
 with sqlite3.connect(db) as c:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert c.execute('select count(*) from ca_province_wages').fetchone()[0]==0
  assert c.execute("select count(*) from sqlite_master where name='bulk_publications'").fetchone()[0]==0


def test_response_lost_after_commit_can_be_retried(tmp_path):
 db=database(tmp_path);p=package();pub.apply(db,p,checksum(p),'isolated-backup')
 # Client never receives the result; same checksum is retried after reconnect.
 result=pub.apply(db,p,checksum(p),'isolated-backup')
 assert result['status']=='already_published' and result['inserted_rows']==0

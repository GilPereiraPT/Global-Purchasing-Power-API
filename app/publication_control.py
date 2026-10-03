"""Private operational evidence for Data Manager; no production auto-publication."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from app.salary_inventory_export import private_path

RECOVERY_TIMEOUT = 30
RECOVERY_TTL = 1800
PREVIEW_TTL = 300
RESERVE = 64 * 1024 * 1024
MAX_DB = 256 * 1024 * 1024


def _private(root):
    root = private_path(root)
    root.mkdir(mode=0o700, exist_ok=True)
    if not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError('Private directory permissions required')
    return root


def _json(path):
    private_path(path)
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Missing or oversized manifest')
    return json.loads(path.read_text())


def _stat(path):
    private_path(path)
    s = path.stat()
    return [s.st_size, s.st_mtime_ns, s.st_ino]


def _write(root, name, data):
    root = _private(root)
    target = private_path(root / name)
    with tempfile.NamedTemporaryFile(dir=root, delete=False) as f:
        temp = Path(f.name)
        f.write(json.dumps(data, sort_keys=True).encode());f.flush();os.fsync(f.fileno())
    try:os.replace(temp, target)
    finally:temp.unlink(missing_ok=True)


def _probe(directory):
    private_path(directory)
    with tempfile.TemporaryFile(dir=directory) as f:
        f.write(b'permission-check');f.flush()
    return True


def database_state():
    from app.store import DB_PATH
    states = {}; fingerprint = {}; total = 0
    for label, variable in (('insights','EARNWAGE_INSIGHTS_DB'),('wages_cache','GPP_CACHE_DB')):
        state = {'status':'unavailable','bytes':0,'wal_bytes':0,'writable':False}
        try:
            raw = os.environ.get(variable,'')
            if not raw:raise ValueError('Missing database')
            path = private_path(Path(raw))
            if label == 'wages_cache' and path.resolve() != Path(DB_PATH).resolve():raise ValueError('Active database mismatch')
            size = path.stat().st_size
            wal = Path(str(path)+'-wal'); wal_size = wal.stat().st_size if wal.exists() else 0
            private_path(wal)
            state.update(bytes=size,wal_bytes=wal_size)
            if size+wal_size > MAX_DB:raise ValueError('Database limit')
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.1) as db:
                db.execute('SELECT count(*) FROM sqlite_master').fetchone()
            writable = os.access(path,os.W_OK) and _probe(path.parent)
            state.update(status='ready' if writable else 'permissions_missing',writable=writable)
            fingerprint[label]={'database':_stat(path),'wal':_stat(wal) if wal.exists() else None,'identity':str(path)}
            total += size+wal_size
        except (OSError,ValueError,sqlite3.Error):pass
        states[label]=state
    if len(fingerprint)==2 and fingerprint['insights']['identity']==fingerprint['wages_cache']['identity']:
        for state in states.values():state['status']='databases_not_distinct'
    return states,fingerprint,total


def backup_identity(root):
    root = _private(root)
    candidates=sorted((p for p in root.iterdir() if re.fullmatch(r'backup-[0-9TZ]+',p.name) and p.is_dir()),reverse=True)
    for folder in candidates:
        if not (folder/'manifest.json').exists():raise ValueError('Latest backup incomplete')
        private_path(folder)
        m=_json(folder/'manifest.json')
        if set(m['databases']) != {'insights','wages_cache'}:raise ValueError('Incomplete backup')
        files={};total=0
        for label, record in m['databases'].items():
            name=label+'.sqlite3';path=folder/name
            if record['file']!=name or record['integrity']!='ok' or not 0<record['bytes']<=MAX_DB:
                raise ValueError('Invalid backup database')
            if path.stat().st_size != record['bytes']:raise ValueError('Incomplete backup file')
            files[name]=_stat(path);total+=record['bytes']
        if len(m['snapshots'])>200:raise ValueError('Snapshot limit')
        for name,record in m['snapshots'].items():
            if record['status']!='backed_up':continue
            if Path(name).name!=name or not name.endswith('.json'):raise ValueError('Invalid snapshot')
            path=folder/name
            if path.stat().st_size != record['bytes']:raise ValueError('Incomplete snapshot')
            files[name]=_stat(path);total+=record['bytes']
        if total>2*MAX_DB+100*1024*1024:raise ValueError('Backup limit')
        return {'backup_id':folder.name,'manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),
                'files':files,'bytes':total}
    return None


def conditions(root, app_root):
    states,_,total=database_state()
    result={'status':'conditions_checked','databases':states,'publication_enabled':os.environ.get('EARNWAGE_BULK_PUBLICATION_ENABLED')=='true',
            'private_writable':False,'free_bytes':None,'required_backup_bytes':None,'space_sufficient':False,
            'backup':{'status':'unavailable'},'recovery_verified':False,'ready':False}
    try:
        _private(root);_probe(root)
        packages=root/'bulk-packages'
        _private(packages);_probe(packages)
        result['private_writable']=True
        snapshots=sum(p.stat().st_size for p in (app_root/'data').glob('*.json') if p.is_file())
        required=3*total+snapshots+RESERVE
        free=shutil.disk_usage(root).free
        result.update(free_bytes=free,required_backup_bytes=required,space_sufficient=free>=required)
        latest=sorted((p.name for p in root.iterdir() if re.fullmatch(r'backup-[0-9TZ]+',p.name) and p.is_dir()),reverse=True)
        if latest:result['backup']['backup_id']=latest[0]
        evidence=backup_identity(root)
        if evidence:
            result['backup']={'status':'available','backup_id':evidence['backup_id'],'bytes':evidence['bytes']}
            try:
                receipt=_json(root/'recovery-proof.json')
                result['recovery_verified']=receipt['backup']==evidence and 0<=time.time()-receipt['tested_at']<RECOVERY_TTL
            except (OSError,ValueError,KeyError,TypeError):pass
        result['ready']=result['private_writable'] and result['space_sufficient'] and result['recovery_verified'] and all(s['status']=='ready' for s in states.values())
    except (OSError,ValueError,KeyError,TypeError):
        result['backup']['status']='unavailable_or_invalid'
    return result


def recovery_worker(backup, output):
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    from scripts.restore_earnwage_data import restore
    from scripts.backup_earnwage_data import digest
    m=_json(Path(backup)/'manifest.json')
    restore(backup,output)
    for label in ('insights','wages_cache'):
        record=m['databases'][label];path=Path(output)/(label+'.sqlite3')
        if path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:raise ValueError('Incomplete restored database')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Recovered integrity failed')
    for name,record in m['snapshots'].items():
        if record['status']=='backed_up' and digest(Path(output)/name)!=record['sha256']:raise ValueError('Restored snapshot mismatch')


def test_recovery(root):
    root=_private(root);_probe(root)
    (root/'recovery-proof.json').unlink(missing_ok=True)
    orphans=list(root.glob('.recovery-*'))
    if len(orphans)>4:raise ValueError('Recovery orphan limit; operator cleanup required')
    for orphan in orphans:
        private_path(orphan)
        if orphan.is_dir() and time.time()-orphan.stat().st_mtime>3600:shutil.rmtree(orphan)
        else:raise ValueError('Recent recovery orphan; operator review required')
    evidence=backup_identity(root)
    if not evidence:return {'status':'recovery_blocked','reason':'backup_unavailable','recovery_verified':False}
    if shutil.disk_usage(root).free < evidence['bytes']+RESERVE:
        return {'status':'recovery_blocked','reason':'insufficient_space','backup_id':evidence['backup_id'],'recovery_verified':False}
    # Revoke old proof before starting; a failed attempt cannot retain approval.
    (root/'recovery-proof.json').unlink(missing_ok=True)
    work=Path(tempfile.mkdtemp(prefix='.recovery-',dir=root));output=work/'restored'
    try:
        script='from app.publication_control import recovery_worker; import sys; recovery_worker(sys.argv[1],sys.argv[2])'
        process=subprocess.run([sys.executable,'-c',script,str(root/evidence['backup_id']),str(output)],
            cwd=Path(__file__).resolve().parent.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=RECOVERY_TIMEOUT)
        if process.returncode!=0:raise ValueError('Recovery verification failed')
        if backup_identity(root)!=evidence:raise ValueError('Backup changed')
        _write(root,'recovery-proof.json',{'backup':evidence,'tested_at':time.time()})
        return {'status':'recovery_verified','backup_id':evidence['backup_id'],'recovery_verified':True,'databases':{label:{'bytes':evidence['files'][label+'.sqlite3'][0], 'integrity':'ok', 'checksum_verified':True, 'complete':True} for label in ('insights','wages_cache')},'valid_for_seconds':RECOVERY_TTL}
    except subprocess.TimeoutExpired:
        return {'status':'recovery_blocked','reason':'timeout','backup_id':evidence['backup_id'],'recovery_verified':False}
    except (OSError,ValueError):
        return {'status':'recovery_blocked','reason':'verification_failed','backup_id':evidence['backup_id'],'recovery_verified':False}
    finally:shutil.rmtree(work)


def record_preview(root, checksum, result):
    _,fingerprint,_=database_state()
    try:evidence=backup_identity(root)
    except (OSError,ValueError,KeyError,TypeError):evidence=None
    _write(root,'salary-review.json',{'checksum':checksum,'result':result,'databases':fingerprint,'backup':evidence,'reviewed_at':time.time()})


def require_ready(root,app_root,checksum,publication=False):
    state=conditions(root,app_root)
    if not state['ready'] or not state['publication_enabled']:raise ValueError('Publication conditions not met')
    if publication:
        review=_json(root/'salary-review.json');_,fingerprint,_=database_state()
        counts=review['result']
        if (review['checksum']!=checksum or not 0<=time.time()-review['reviewed_at']<PREVIEW_TTL
            or review['databases']!=fingerprint or review.get('backup')!=backup_identity(root) or counts['inserted_rows']<=0
            or counts['duplicate_rows'] or counts['protected_existing_rows']):raise ValueError('Fresh conflict-free preview required')
    return state

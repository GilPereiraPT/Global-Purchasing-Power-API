"""Bounded offline bulk acquisition and versioned SQLite staging, no HTTP routes."""
import hashlib
import json
import math
import re
import sqlite3
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

import httpx

HOSTS = {'api.worldbank.org','ec.europa.eu','www.bls.gov','open.canada.ca','opencanada.blob.core.windows.net','datasets.cbs.nl'}
MAX_FILE = 96 * 1024 * 1024
BATCH_SIZE = 250


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):
            h.update(chunk)
    return h.hexdigest()


def valid_url(url):
    p=urlsplit(url)
    if p.hostname == 'datasets.cbs.nl' and not (
            p.path in {'/odata/v1/CBS/86355NED' + suffix for suffix in
                       ('', '/Properties', '/BeroepCodes', '/PeriodenCodes',
                        '/MeasureCodes', '/Observations', '/$metadata')}):
        raise ValueError('Unregistered CBS dataset destination')
    if p.hostname=='opencanada.blob.core.windows.net' and not p.path.startswith('/opengovprod/resources/'):
        raise ValueError('Unregistered public catalogue destination')
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Only registered public HTTPS provider URLs are permitted')


class Downloader:
    """Stream files; cache complete checksummed responses, never partial bodies.

    Import/page checkpoints resume jobs. Interrupted single HTTP objects restart;
    no Range resume is claimed without a verified provider range contract.
    """
    def __init__(self, cache, client=None, sleep=time.sleep, interval=1.0, attempts=3, max_bytes=MAX_FILE):
        if not math.isfinite(interval) or interval<1 or not 1<=attempts<=5 or not 1<=max_bytes<=MAX_FILE:
            raise ValueError('Invalid download limits')
        self.cache=Path(cache)
        self.cache.mkdir(parents=True,exist_ok=True)
        self.client=client or httpx.Client(timeout=httpx.Timeout(60,connect=15),follow_redirects=False)
        self.sleep=sleep
        self.interval=interval
        self.attempts=attempts
        self.max_bytes=max_bytes

    def close(self):
        self.client.close()

    def get(self,url,ttl=0):
        valid_url(url)
        key=hashlib.sha256(url.encode()).hexdigest()
        meta_path=self.cache/(key+'.json')
        body_path=self.cache/(key+'.body')
        part=self.cache/(key+'.part')
        try:
            meta=json.loads(meta_path.read_text())
        except (FileNotFoundError,ValueError):
            meta={}
        cached=(body_path.is_file() and body_path.stat().st_size<=self.max_bytes
                and meta.get('sha256')==digest(body_path) and meta.get('url')==url)
        if cached and ttl>0 and time.time()-meta.get('checked_at',0)<ttl:
            return body_path,{**meta,'cache_status':'fresh'}
        headers={'User-Agent':'EarnWage-Bulk/1.0','Accept-Encoding':'identity'}
        if cached:
            for field,header in (('etag','If-None-Match'),('last_modified','If-Modified-Since')):
                if meta.get(field):headers[header]=meta[field]
        try:
            for attempt in range(self.attempts):
                self.sleep(self.interval)
                retry_delay=None
                try:
                    current=url
                    for redirects in range(5):
                        with self.client.stream('GET',current,headers=headers) as response:
                            if response.status_code in (301,302,303,307,308):
                                from urllib.parse import urljoin
                                current=urljoin(current,response.headers['location'])
                                valid_url(current)
                                # Conditional credentials never travel to another host.
                                if urlsplit(current).hostname!=urlsplit(url).hostname:
                                    headers={'User-Agent':'EarnWage-Bulk/1.0','Accept-Encoding':'identity'}
                                self.sleep(self.interval)
                                continue
                            if response.status_code==304:
                                if not cached:raise ValueError('304 without verified cached file')
                                meta['checked_at']=time.time()
                                meta_path.write_text(json.dumps(meta))
                                return body_path,{**meta,'cache_status':'not_modified'}
                            if response.status_code==429 or 500<=response.status_code<=599:
                                raw=response.headers.get('retry-after')
                                if raw:
                                    from email.utils import parsedate_to_datetime
                                    try: retry_delay=float(raw)
                                    except ValueError: retry_delay=parsedate_to_datetime(raw).timestamp()-time.time()
                                    if not math.isfinite(retry_delay) or retry_delay>60:
                                        raise ValueError('Provider requested a longer pause; stop and schedule later')
                                    retry_delay=max(0,retry_delay)
                                response.raise_for_status()
                            response.raise_for_status()
                            if response.status_code!=200:
                                raise ValueError('Partial/unexpected HTTP response')
                            total=0
                            with part.open('wb') as f:
                                for chunk in response.iter_bytes(65536):
                                    total+=len(chunk)
                                    if total>self.max_bytes:raise ValueError('Download exceeds configured size')
                                    f.write(chunk)
                            if total==0:raise ValueError('Empty download')
                            checksum=digest(part)
                            part.replace(body_path)
                            meta={'url':url,'resolved_url':current.split('?')[0] if urlsplit(current).hostname=='opencanada.blob.core.windows.net' else current,'sha256':checksum,
                                  'bytes':total,'etag':response.headers.get('etag'),
                                  'last_modified':response.headers.get('last-modified'),
                                  'content_type':response.headers.get('content-type'),
                                  'checked_at':time.time(),'fetched_at':utcnow()}
                            meta_path.write_text(json.dumps(meta))
                            return body_path,{**meta,'cache_status':'downloaded'}
                    raise ValueError('Too many redirects')
                except (httpx.TransportError,httpx.HTTPStatusError) as error:
                    part.unlink(missing_ok=True)
                    transient=(not isinstance(error,httpx.ProxyError) and
                               (isinstance(error,httpx.TransportError) or error.response.status_code==429
                                or 500<=error.response.status_code<=599))
                    if not transient or attempt+1==self.attempts:raise
                    self.sleep(max(2**attempt,retry_delay or 0))
        finally:
            part.unlink(missing_ok=True)


class BulkStore:
    """Independent staging DB. All accepted revisions retain original provenance.

    Revisions over the configured relative threshold (same observation or last
    known period of identical dimensions) are quarantined and never replace it.
    """
    def __init__(self,path,variation_limit=Decimal('.30')):
        self.path=Path(path)
        if not Decimal('0')<variation_limit<=Decimal('1'):
            raise ValueError('Invalid review threshold')
        self.variation_limit=variation_limit
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=15)
        self.db.execute('PRAGMA busy_timeout=15000')
        existing={r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if existing and 'bulk_runs' not in existing:
            self.db.close()
            raise ValueError('Refusing to initialize staging in an existing application database')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS bulk_runs (
            id INTEGER PRIMARY KEY, provider TEXT NOT NULL,dataset TEXT NOT NULL,
            started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,
            error_type TEXT,before_count INTEGER,after_count INTEGER);
        CREATE TABLE IF NOT EXISTS bulk_run_results (
            run_id INTEGER PRIMARY KEY,result TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bulk_artifacts (
            sha256 TEXT NOT NULL,url TEXT NOT NULL,metadata TEXT NOT NULL,
            PRIMARY KEY(sha256,url));
        CREATE TABLE IF NOT EXISTS bulk_versions (
            key TEXT NOT NULL,version TEXT NOT NULL,value TEXT NOT NULL,
            payload TEXT NOT NULL,status TEXT NOT NULL,reason TEXT,
            imported_at TEXT NOT NULL,PRIMARY KEY(key,version));
        CREATE TABLE IF NOT EXISTS bulk_current (
            key TEXT PRIMARY KEY,version TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bulk_progress (
            job TEXT NOT NULL,checksum TEXT NOT NULL,offset INTEGER NOT NULL,
            PRIMARY KEY(job,checksum));
        ''')
        self.db.execute("CREATE INDEX IF NOT EXISTS bulk_lookup ON bulk_current(json_extract(payload,'$.country'),json_extract(payload,'$.indicator'))")
        self.db.execute("CREATE INDEX IF NOT EXISTS bulk_version_lookup ON bulk_versions(json_extract(payload,'$.country'),json_extract(payload,'$.indicator'))")
        columns={r[1] for r in self.db.execute('PRAGMA table_info(bulk_versions)')}
        if 'series_key' not in columns:
            self.db.execute('ALTER TABLE bulk_versions ADD COLUMN series_key TEXT')
            for key,version,payload in self.db.execute('SELECT key,version,payload FROM bulk_versions').fetchall():
                self.db.execute('UPDATE bulk_versions SET series_key=? WHERE key=? AND version=?',
                                (observation_key(json.loads(payload),series=True),key,version))
        self.db.execute('CREATE INDEX IF NOT EXISTS bulk_series ON bulk_versions(series_key)')
        self.db.commit()

    def close(self):self.db.close()

    def count(self):return self.db.execute('SELECT COUNT(*) FROM bulk_current').fetchone()[0]

    def start(self,provider,dataset):
        with self.db:
            cursor=self.db.execute('INSERT INTO bulk_runs(provider,dataset,started_at,status,before_count) VALUES (?,?,?,?,?)',
                                   (provider,dataset,utcnow(),'running',self.count()))
        return cursor.lastrowid

    def finish(self,run,status,error=None,result=None):
        with self.db:
            self.db.execute('UPDATE bulk_runs SET finished_at=?,status=?,error_type=?,after_count=? WHERE id=?',
                            (utcnow(),status,error,self.count(),run))
            if result is not None:
                self.db.execute('INSERT OR REPLACE INTO bulk_run_results VALUES (?,?)',(run,json.dumps(result,sort_keys=True)))

    def artifact(self,meta):
        if not re.fullmatch('[a-f0-9]{64}',meta.get('sha256','')):raise ValueError('Invalid checksum')
        valid_url(meta['url'])
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO bulk_artifacts VALUES (?,?,?)',
                            (meta['sha256'],meta['url'],json.dumps(meta,sort_keys=True)))

    def ingest(self,job,checksum,rows,batch_size=BATCH_SIZE):
        if not 1<=batch_size<=1000:raise ValueError('Invalid batch size')
        if not self.db.execute('SELECT 1 FROM bulk_artifacts WHERE sha256=?',(checksum,)).fetchone():
            raise ValueError('Import requires registered artifact')
        progress=self.db.execute('SELECT offset FROM bulk_progress WHERE job=? AND checksum=?',(job,checksum)).fetchone()
        offset=progress[0] if progress else 0
        counts={'accepted':0,'quarantined':0,'duplicates':0,'missing':0,'resumed_rows':offset}
        batch=[]
        for index,row in enumerate(rows,1):
            if index<=offset:continue
            batch.append((index,row))
            if len(batch)>=batch_size:
                self._batch(job,checksum,batch,counts)
                batch=[]
        if batch:self._batch(job,checksum,batch,counts)
        return counts

    def _batch(self,job,checksum,batch,counts):
        with self.db:
            for index,row in batch:
                key_fields=('provider','dataset','country','geography','indicator','classification',
                            'measure','unit','currency','period')
                required=set(key_fields)|{'value','source_url','flags'}
                if not required<=row.keys():raise ValueError('Missing observation dimensions')
                from app.catalog import COUNTRY_MAP
                if row['country'] not in COUNTRY_MAP or not valid_geography(row):
                    raise ValueError('Unknown country or unverified region')
                valid_url(row['source_url'])
                if isinstance(row['value'],bool):raise ValueError('Boolean observation')
                missing=row['value'] is None
                if missing and row['provider'] not in ('bls','job_bank'):raise ValueError('Unregistered missing observation')
                try:value=Decimal('0') if missing else Decimal(str(row['value']))
                except InvalidOperation:raise ValueError('Invalid numeric observation') from None
                if not value.is_finite() or abs(value)>Decimal('1e12'):
                    raise ValueError('Non-finite or out-of-range value')
                if not re.fullmatch(r'(19|20)\d{2}(-(?:0[1-9]|1[0-2]))?',row['period']) and not (row['provider']=='job_bank' and missing and row['period']=='unknown') and not (row['provider']=='job_bank' and re.fullmatch(r'(19|20)\d{2}-(19|20)\d{2}',row['period']) and row['period'][:4]<=row['period'][-4:]):
                    raise ValueError('Invalid reference period')
                dimensions={k:row[k] for k in key_fields}
                key=observation_key(row)
                series_key=observation_key(row,series=True)
                row={**row,'artifact_sha256':checksum}
                payload=json.dumps(row,sort_keys=True,separators=(',',':'))
                # Checksum records the acquisition version even when its value is unchanged.
                version=hashlib.sha256((checksum+payload).encode()).hexdigest()
                if self.db.execute('SELECT 1 FROM bulk_versions WHERE key=? AND version=?',(key,version)).fetchone():
                    counts['duplicates']+=1
                    continue
                previous=self.db.execute('SELECT payload FROM bulk_current WHERE key=?',(key,)).fetchone()
                if previous is None:
                    previous=self.db.execute("SELECT payload FROM bulk_versions WHERE key=? AND status='accepted' ORDER BY imported_at DESC LIMIT 1",(key,)).fetchone()
                is_revision=previous is not None
                if previous is None:
                    # Compare adjacent published candidates, including quarantined ones.
                    # Do not freeze a growing series against one old accepted anchor.
                    # Existing-key revisions always compare the accepted value above.
                    candidates=self.db.execute('SELECT payload FROM bulk_versions WHERE series_key=? AND status!=? ORDER BY imported_at DESC', (series_key,'missing'))
                    prior=None
                    later=None
                    for item in candidates:
                        p=json.loads(item[0])
                        if p['period']<row['period'] and all(p[k]==row[k] for k in key_fields if k!='period'):
                            if prior is None or p['period']>prior['period']:prior=p
                        elif p['period']>row['period'] and all(p[k]==row[k] for k in key_fields if k!='period'):
                            if later is None or p['period']<later['period']:later=p
                    nearest=prior or later
                    previous=(json.dumps(nearest),) if nearest else None
                suspect=False
                if previous and not missing:
                    old=Decimal(str(json.loads(previous[0])['value']))
                    if not is_revision and ('percent' in row['unit'] or row['unit'] in ('index_0_100','governance_score_0_100')):
                        suspect=abs(value-old)>Decimal('10')
                    else:
                        suspect=(value!=old if old==0 else abs(value-old)/abs(old)>self.variation_limit)
                flag_review=row['provider']=='eurostat' and any(f in row['flags'] for f in 'bdu')
                status='missing' if missing else 'quarantined' if suspect or flag_review else 'accepted'
                reason=('provider_quality_or_methodology_flag' if flag_review else
                        'unexpected_revision_or_temporal_variation' if suspect else None)
                self.db.execute('INSERT INTO bulk_versions(key,version,value,payload,status,reason,imported_at,series_key) VALUES (?,?,?,?,?,?,?,?)',
                                (key,version,'' if missing else str(value),payload,status,reason,utcnow(),series_key))
                if status=='accepted':
                    self.db.execute('INSERT INTO bulk_current VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET version=excluded.version,payload=excluded.payload',
                                    (key,version,payload))
                elif status=='missing':
                    self.db.execute('DELETE FROM bulk_current WHERE key=?',(key,))
                counts[status]+=1
            self.db.execute('INSERT INTO bulk_progress VALUES (?,?,?) ON CONFLICT(job,checksum) DO UPDATE SET offset=excluded.offset',
                            (job,checksum,batch[-1][0]))

    def report(self):
        return {'accepted_observations':self.count(),
                'missing_versions':self.db.execute("SELECT COUNT(*) FROM bulk_versions WHERE status='missing'").fetchone()[0],
                'by_source':dict(self.db.execute("SELECT json_extract(payload,'$.provider'),COUNT(*) FROM bulk_current GROUP BY 1")),
                'quarantined_versions':self.db.execute("SELECT COUNT(*) FROM bulk_versions WHERE status='quarantined'").fetchone()[0],
                'artifacts':self.db.execute('SELECT COUNT(*) FROM bulk_artifacts').fetchone()[0],
                'quarantined_observations':[json.loads(r[0]) for r in self.db.execute("SELECT payload FROM bulk_versions WHERE status='quarantined'")],
                'runs':[{**dict(zip(('id','provider','dataset','started_at','finished_at','status','error_type','before_count','after_count'),r)),
                         'result':json.loads(detail[0]) if (detail:=self.db.execute('SELECT result FROM bulk_run_results WHERE run_id=?',(r[0],)).fetchone()) else None}
                        for r in self.db.execute('SELECT * FROM bulk_runs')]}


KEY_FIELDS=('provider','dataset','country','geography','indicator','classification','measure','unit','currency','period')

def observation_key(row,series=False):
    dimensions={k:row[k] for k in KEY_FIELDS if not (series and k=='period')}
    if row.get('dimensions'):
        if not isinstance(row['dimensions'],dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in row['dimensions'].items()):
            raise ValueError('Dimensions must be explicit string identifiers')
        dimensions['dimensions']=row['dimensions']
    return hashlib.sha256(json.dumps(dimensions,sort_keys=True).encode()).hexdigest()

def valid_geography(row):
    geo=row['geography']
    if geo=='national':return True
    if row['provider']=='bls' and row['country']=='US':
        return bool(re.fullmatch(r'BLS:[2346]:[0-9]{2,7}',geo))
    if row['provider']=='job_bank' and row['country']=='CA':
        return bool(re.fullmatch(r'CA:(?:province:[A-Z]{2}|economic_region:ER[0-9]{4})',geo))
    return False

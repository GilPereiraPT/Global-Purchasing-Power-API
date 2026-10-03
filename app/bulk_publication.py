"""Bounded data-only packages projected into existing wage tables.

No network, SQL payloads, deployment or environment mutation. The authenticated
Data Manager owns authorization, fixed server paths, lock and fresh backups.
Missing/quarantined values and unrepresentable source scopes are not published.
"""
from collections import defaultdict
from contextlib import closing
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from app.bulk_classifications import require_mapping
from app.bulk_core import observation_key
from app.north_america import CANADA_NOC, CANADA_DATASET, CANADA_URL, US_SOC
from app.bulk_bls import url as bls_url

SCHEMA='earnwage-reviewed-salary-package-v1'
MAX_BYTES=2*1024*1024
MAX_OBSERVATIONS=1000
MAX_DATABASE_BYTES=256*1024*1024
TABLES={'us_oews','north_america_wages','ca_province_wages'}
PRIMARY_KEYS={
 'us_oews':('reference_period','source_file','area','area_type','prim_state','naics','i_group','own_code','occ_code'),
 'north_america_wages':('country','occupation','geography','classification','reference_period','measure','source'),
 'ca_province_wages':('occupation','province','classification','reference_period','measure','source'),
}


def encode(package):
    return (json.dumps(package,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def projection(row):
    """Return an existing-table projection, or an explicit unsupported reason."""
    provider=row['provider']; country=row['country']
    jobs=row.get('occupations',[])
    if not jobs or len(jobs)!=len(set(jobs)):raise ValueError('Missing or duplicate reviewed occupations')
    system,code=row['classification'].split(':',1)
    for job in jobs:require_mapping(country,job,system,code)
    value=Decimal(row['value'])
    if not value.is_finite() or not 0<value<Decimal('1e12'):raise ValueError('Invalid published salary')
    if Decimal(str(float(value)))!=value:raise ValueError('Salary cannot be represented by existing REAL schema')
    if row.get('flags'):raise ValueError('Flagged salary cannot be published')
    if not re.fullmatch('[0-9a-f]{64}',row.get('artifact_sha256','')):raise ValueError('Source checksum required')
    if row['indicator']!='occupational_salary':raise ValueError('Unsupported indicator')
    if provider=='bls':
        year=int(row['period'])
        if country!='US' or row['dataset']!='OEWS' or row['source_url']!=bls_url(year) or row['currency']!='USD':raise ValueError('Unverified BLS release')
        if row['dimensions']!={'industry':'000000','ownership':'1235','occupation_group':'detailed'}:raise ValueError('Unsupported BLS population')
        if row['unit'] not in ('USD/hour','USD/year') or row['measure'] not in ('mean','median','pct10','pct25','pct75','pct90'):raise ValueError('Unverified wage measure')
        if row['original_period']!=f'May {year}' or Decimal(str(row['original_salary_token']))!=value:raise ValueError('Original observation mismatch')
        # Historical staging has no original prim_state. Do not infer it from
        # geography names, nor silently publish unusable regional records.
        if row['geography']!='national':return [],'bls_regional_metadata_not_in_package_scope'
        if row['original_area']!='99' or row['original_area_type']!='1' or row['geography_name']!='U.S.':raise ValueError('Invalid national source scope')
        field=('h_' if row['unit']=='USD/hour' else 'a_')+row['measure']
        title=next(title for soc,title in US_SOC.values() if soc==code)
        identity={'published_year':year,'area':'99','area_type':'1','naics':'000000','own_code':'1235','occ_code':code,'o_group':'detailed'}
        base={'reference_period':row['original_period'],'published_year':year,
              'source_file':Path(row['source_member']).name,'area':'99','area_title':'U.S.',
              'area_type':'1','prim_state':'','naics':'000000','naics_title':'',
              'i_group':'','own_code':'1235','occ_code':code,'occ_title':title,
              'o_group':'detailed','source_url':row['source_url']}
        return [('us_oews',identity,base,field,str(value))],None
    if provider!='job_bank' or country!='CA' or row['dataset']!='JobBank2025' or row['source_url']!=CANADA_URL or row['currency']!='CAD':raise ValueError('Unverified salary source')
    from app.bulk_job_bank import LICENCE
    if row.get('licence_url')!=LICENCE or row['dimensions']!={'classification_version':'NOC2021'}:raise ValueError('Unverified licence or classification')
    if row['unit'] not in ('CAD/hour','CAD/year') or row['measure'] not in ('low','median','high','mean','p25','p75'):raise ValueError('Unverified wage measure')
    if row['period']!=row['original_period'] or not re.fullmatch(r'20\d{2}(?:-20\d{2})?',row['period']):raise ValueError('Unverified salary period')
    geo=row['geography']
    if geo.startswith('CA:economic_region:'):return [],'canadian_economic_region_has_no_existing_api_table'
    if geo=='national' and row['measure'] not in ('mean','median'):return [],'national_api_measure_not_supported'
    if geo!='national' and not geo.startswith('CA:province:'):raise ValueError('Unsupported salary geography')
    from app.ca_province_wages import SOURCE_PROVINCES
    if geo=='national':
        if row.get('original_province')!='NAT' or row.get('original_geography')!='ER00':raise ValueError('Invalid national source scope')
    else:
        province=geo.split(':')[2]
        if SOURCE_PROVINCES.get(row.get('original_province'))!=(province,row.get('original_geography')):raise ValueError('Invalid provincial source scope')
    result=[]
    for job in jobs:
        title=CANADA_NOC[job][1]
        base={'occupation':job,'classification':row['classification'],'job_title':title,
              'reference_period':row['period'],'published_year':2025,'measure':row['measure'],
              'unit':row['unit'],'value':str(value),'source':CANADA_DATASET,'source_url':CANADA_URL}
        if geo=='national':base.update(country='CA',geography='national',currency='CAD');table='north_america_wages'
        else:base['province']=geo.split(':')[2];table='ca_province_wages'
        fields=('country','occupation','geography','classification','reference_period','measure','source') if geo=='national' else ('occupation','province','classification','reference_period','measure','source')
        result.append((table,{k:base[k] for k in fields},base,'value',str(value)))
    return result,None


def validate(package):
    if set(package)!={'schema','observations'} or package['schema']!=SCHEMA:raise ValueError('Unknown publication schema')
    rows=package['observations']
    if not isinstance(rows,list) or not 0<len(rows)<=MAX_OBSERVATIONS:raise ValueError('Publication observation limit')
    keys=set()
    for row in rows:
        key=observation_key(row)
        if key in keys:raise ValueError('Duplicate package observation')
        keys.add(key)
        targets,reason=projection(row)
        if reason or not targets:raise ValueError('Unrepresentable publication scope')
    return rows


def load(path,checksum):
    path=Path(path)
    if not re.fullmatch('[0-9a-f]{64}',checksum) or path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES:raise ValueError('Unsafe publication package')
    raw=path.read_bytes()
    if len(raw)>MAX_BYTES or hashlib.sha256(raw).hexdigest()!=checksum:raise ValueError('Publication checksum mismatch')
    package=json.loads(raw);validate(package)
    if raw!=encode(package):raise ValueError('Canonical package encoding required')
    return package


def build(staging,limit=MAX_OBSERVATIONS):
    """Export complete target rows in bounded batches from accepted staging only.

    Deterministic grouping keeps one OEWS row's accepted measures together.
    No production baseline is discovered. Repeated packages remain idempotent.
    """
    if not isinstance(limit,int) or not 1<=limit<=MAX_OBSERVATIONS:raise ValueError('Invalid package limit')
    path=Path(staging)
    if path.is_symlink() or not path.is_file():raise ValueError('Explicit regular staging file required')
    groups=defaultdict(list);excluded=defaultdict(int)
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        if any(status!='complete' for status, in db.execute('SELECT status FROM bulk_runs WHERE id IN (SELECT MAX(id) FROM bulk_runs GROUP BY provider,dataset)')):raise ValueError('Incomplete acquisition')
        # Unsupported regional scopes are counted in SQL, not loaded into RAM.
        for payload, in db.execute("SELECT payload FROM bulk_current WHERE json_extract(payload,'$.geography')='national' OR json_extract(payload,'$.geography') LIKE 'CA:province:%' ORDER BY key"):
            row=json.loads(payload)
            if row['provider'] not in ('bls','job_bank'):continue
            version=db.execute('SELECT status FROM bulk_versions WHERE key=? AND version=(SELECT version FROM bulk_current WHERE key=?)',(observation_key(row),observation_key(row))).fetchone()
            if not version or version[0]!='accepted':raise ValueError('Staging status mismatch')
            if not db.execute('SELECT 1 FROM bulk_artifacts WHERE sha256=? AND url=?',(row['artifact_sha256'],row['source_url'])).fetchone():raise ValueError('Unregistered source artifact')
            targets,reason=projection(row)
            if reason:excluded[reason]+=1;continue
            identity=(row['provider'],row['classification'],row['geography'],row['period'])
            groups[identity].append(row)
            if sum(map(len,groups.values()))>20000:raise ValueError('Offline selection exceeds memory budget')
        for provider,geo,n in db.execute("SELECT json_extract(payload,'$.provider'),json_extract(payload,'$.geography'),COUNT(*) FROM bulk_current WHERE json_extract(payload,'$.geography')!='national' AND json_extract(payload,'$.geography') NOT LIKE 'CA:province:%' GROUP BY 1,2"):
            if provider=='bls':excluded['bls_regional_metadata_not_in_package_scope']+=n
            elif provider=='job_bank':excluded['canadian_economic_region_has_no_existing_api_table']+=n
    # Eligible national/provincial subset is ~5k cells; avoid full acquisition archive.
    batch=[];packages=[]
    for _,rows in sorted(groups.items()):
        if len(rows)>limit:raise ValueError('Target row exceeds package limit')
        if len(batch)+len(rows)>limit:packages.append({'schema':SCHEMA,'observations':batch});batch=[]
        batch.extend(sorted(rows,key=observation_key))
    if batch:packages.append({'schema':SCHEMA,'observations':batch})
    for package in packages:
        validate(package)
        if len(encode(package))>MAX_BYTES:raise ValueError('Package exceeds byte budget')
    return packages,dict(excluded)


def _connect(path, readonly=False):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or 'public_html' in path.resolve().parts:raise ValueError('Existing private database required')
    if path.stat().st_size>MAX_DATABASE_BYTES:raise ValueError('Database exceeds shared-hosting backup budget')
    db=sqlite3.connect(path.resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw'),uri=True,timeout=5)
    db.execute('PRAGMA busy_timeout=5000')
    return db


def _targets(package):
    grouped={}
    for row in validate(package):
        for table,identity,base,field,value in projection(row)[0]:
            key=(table,json.dumps(identity,sort_keys=True))
            if key not in grouped:grouped[key]=(table,identity,dict(base),{})
            values=grouped[key][3]
            if field in values and Decimal(values[field])!=Decimal(value):raise ValueError('Conflicting target values')
            values[field]=value
    for table,identity,base,values in grouped.values():base.update(values)
    return list(grouped.values())


def _plan(db,targets):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    changes=[];duplicate=conflict=0
    for table,identity,base,values in targets:
        columns=list(base)
        if table not in tables:
            changes.append((table,base));continue
        info=db.execute('PRAGMA table_info('+table+')').fetchall()
        schema={r[1] for r in info}
        primary=tuple(r[1] for r in sorted((r for r in info if r[5]),key=lambda r:r[5]))
        if not set(columns)<=schema or primary!=PRIMARY_KEYS[table]:raise ValueError('Incompatible target database schema')
        where=' AND '.join(k+'=?' for k in identity)
        existing=db.execute('SELECT '+','.join(values)+' FROM '+table+' WHERE '+where,tuple(identity.values())).fetchall()
        if len(existing)>1:raise ValueError('Ambiguous existing target observations')
        if not existing:changes.append((table,base));continue
        metadata_ok=True
        if table!='us_oews':
            metadata=db.execute('SELECT unit,source_url FROM '+table+' WHERE '+where,tuple(identity.values())).fetchone()
            metadata_ok=metadata==(base['unit'],base['source_url'])
        if metadata_ok and all(a is not None and Decimal(str(a))==Decimal(values[k]) for k,a in zip(values,existing[0])):duplicate+=1
        else:conflict+=1
    return changes,{'inserted_rows':len(changes),'duplicate_rows':duplicate,'protected_existing_rows':conflict}


def preview(path,package):
    with closing(_connect(path, readonly=True)) as db:
        db.execute('PRAGMA query_only=ON')
        _,result=_plan(db,_targets(package))
        return result


def apply(path,package,checksum,backup_id,*,require_clean=False):
    if not backup_id or not re.fullmatch('[0-9a-f]{64}',checksum) or hashlib.sha256(encode(package)).hexdigest()!=checksum:raise ValueError('Verified package and fresh backup required')
    with closing(_connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            # Validate schema BEFORE init/migration, and recheck plan under writer lock.
            targets=_targets(package);changes,result=_plan(db,targets)
            if require_clean and (result["protected_existing_rows"] or result["duplicate_rows"] or not changes):
                raise ValueError("Publication conflicts under transaction lock")
            from app.us_oews import init as us_init
            from app.north_america import init as ca_init
            from app.ca_province_wages import init as province_init
            initializers={"us_oews":us_init,"north_america_wages":ca_init,"ca_province_wages":province_init}
            for table in sorted({t[0] for t in changes}):initializers[table](db)
            db.execute('CREATE TABLE IF NOT EXISTS bulk_publications (checksum TEXT PRIMARY KEY, backup_id TEXT NOT NULL, inserted_json TEXT NOT NULL, status TEXT NOT NULL)')
            prior=db.execute('SELECT status FROM bulk_publications WHERE checksum=?',(checksum,)).fetchone()
            if prior:
                db.rollback();return {**result,'status':'already_'+prior[0]}
            journal=[]
            for table,base in changes:
                columns=list(base)
                db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(base.values()))
                # Capture full resulting row, including NULL/defaults, for guarded rollback.
                rowid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                cursor=db.execute('SELECT * FROM '+table+' WHERE rowid=?',(rowid,))
                names=[x[0] for x in cursor.description];journal.append({'table':table,'rowid':rowid,'row':dict(zip(names,cursor.fetchone()))})
            db.execute('INSERT INTO bulk_publications VALUES (?,?,?,?)',(checksum,backup_id,json.dumps(journal,sort_keys=True),'published'))
            db.commit();return {**result,'status':'published','checksum':checksum,'backup_id':backup_id}
        except Exception:db.rollback();raise


def rollback(path,checksum):
    if not re.fullmatch('[0-9a-f]{64}',checksum):raise ValueError('Invalid publication checksum')
    with closing(_connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            record=db.execute('SELECT inserted_json,status FROM bulk_publications WHERE checksum=?',(checksum,)).fetchone()
            if not record:raise ValueError('Unknown publication')
            if record[1]=='rolled_back':db.rollback();return {'status':'already_rolled_back'}
            journal=json.loads(record[0])
            if len(journal)>MAX_OBSERVATIONS*2:raise ValueError('Rollback limit')
            for item in journal:
                table=item['table']
                if table not in TABLES:raise ValueError('Invalid rollback journal')
                cur=db.execute('SELECT * FROM '+table+' WHERE rowid=?',(item['rowid'],))
                row=cur.fetchone()
                if row is None or dict(zip([x[0] for x in cur.description],row))!=item['row']:raise ValueError('Published data changed; manual recovery required')
            for item in journal:db.execute('DELETE FROM '+item['table']+' WHERE rowid=?',(item['rowid'],))
            db.execute("UPDATE bulk_publications SET status='rolled_back' WHERE checksum=?",(checksum,))
            db.commit();return {'status':'rolled_back','removed_rows':len(journal)}
        except Exception:db.rollback();raise

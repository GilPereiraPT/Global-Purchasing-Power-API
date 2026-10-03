"""OEWS bulk adapter using the existing workbook parser and Phase 4 ledger.

SOC2018 releases 2021–2025 only. Earlier hybrid/2010 and XLS releases are
explicitly unavailable until classification crosswalks/layouts are reviewed.
Validates all source rows; stages approved EarnWage codes, cross-industry,
all ownerships, national/state/metro/nonmetro. No inferred wages.
"""
import hashlib
import tempfile
import zipfile
from pathlib import Path
from app.us_oews import workbook_records, _safe_zip_members, WAGE_FIELDS
from app.north_america import US_SOC

YEARS=tuple(range(2021,2026))
DATASETS={str(y):y for y in YEARS}
SOC_SOURCE='https://www.bls.gov/oes/oes_ques.htm'


def url(year):
    if year not in YEARS:raise ValueError('Unvalidated SOC release year')
    return f'https://www.bls.gov/oes/special-requests/oesm{year%100:02d}all.zip'


def observations(path,year,stats):
    by_code={}
    for occupation,(code,title) in US_SOC.items():by_code.setdefault(code,[]).append(occupation)
    seen=set()
    stats.update(source_rows=0,selected_rows=0,excluded_rows=0,missing_wages=0)
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory(prefix='earnwage-oews-') as tmp:
        members=list(_safe_zip_members(z))
        if not members:raise ValueError('No XLSX release member')
        for member in members:
            target=Path(tmp)/Path(member.filename).name
            with z.open(member) as source,target.open('wb') as dest:
                import shutil
                shutil.copyfileobj(source,dest)
            with zipfile.ZipFile(target) as workbook:
                if sum(m.file_size for m in workbook.infolist())>1_500_000_000:
                    raise ValueError('Workbook expansion exceeds limit')
            for row in workbook_records(target,year,bulk=True):
                stats['source_rows']+=1
                if stats['source_rows']>1_000_000:raise ValueError('Release exceeds row limit')
                identity=tuple(row[k] for k in ('area','area_type','prim_state','naics','i_group','own_code','occ_code'))
                key=hashlib.sha256(repr(identity).encode()).digest()
                if key in seen:raise ValueError('Duplicate BLS source identity')
                seen.add(key)
                area_type=row['area_type']
                if area_type not in ('1','2','3','4','6'):raise ValueError('Unvalidated BLS geography type')
                if not row['area'].isdigit() or not row['area_title']:raise ValueError('Invalid BLS geography')
                if row['occ_code'] not in by_code or row['o_group']!='detailed' or row['naics']!='000000' or row['own_code']!='1235':
                    stats['excluded_rows']+=1
                    continue
                if area_type=='1' and (row['area']!='99' or row['area_title']!='U.S.'):
                    raise ValueError('Unvalidated national geography')
                if row['occ_title'].casefold()!=next(title for code,title in US_SOC.values() if code==row['occ_code']).casefold():
                    raise ValueError('SOC title drift')
                stats['selected_rows']+=1
                for field in WAGE_FIELDS:
                    value=row[field.lower()]
                    if value is not None and value<0:raise ValueError('Negative wage')
                    if value is None:stats['missing_wages']+=1
                    hourly=field.startswith('H_')
                    yield {'provider':'bls','dataset':'OEWS','country':'US',
                        'geography':'national' if area_type=='1' else f"BLS:{area_type}:{row['area']}",
                        'geography_name':row['area_title'],'original_area':row['area'],'original_area_type':area_type,'original_prim_state':row['prim_state'],
                        'indicator':'occupational_salary','classification':'SOC2018:'+row['occ_code'],
                        'original_occupation_title':row['occ_title'],'occupations':by_code[row['occ_code']],'classification_source':SOC_SOURCE,
                        'measure':field[2:].lower(),'unit':'USD/hour' if hourly else 'USD/year','currency':'USD',
                        'period':str(year),'original_period':row['reference_period'],'value':None if value is None else str(value),
                        'original_salary_token':row['raw_wages'][field],
                        'source_url':url(year),'source_member':member.filename,'flags':row['raw_wages'][field] if value is None else '',
                        'dimensions':{'industry':row['naics'],'ownership':row['own_code'],'occupation_group':row['o_group']}}


def run(store,downloader,name,ttl=0):
    year=DATASETS[name];run_id=store.start('bls',name)
    stats={}
    try:
        path,artifact=downloader.get(url(year),ttl=ttl);store.artifact(artifact)
        counts=store.ingest('bls:'+name,artifact['sha256'],observations(path,year,stats),batch_size=1000)
        result={**counts,**stats,'acquisition_mode':'live_bulk','source_url':url(year),
                'acquired_at':artifact['fetched_at'],'artifact_sha256':artifact['sha256']}
        store.finish(run_id,'complete',result=result);return result
    except Exception as error:
        store.finish(run_id,'failed',type(error).__name__,result=stats);raise

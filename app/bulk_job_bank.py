"""Validated Job Bank 2025 adapter for the existing Phase 4 staging pipeline."""
import json
from pathlib import Path
from app.north_america import CANADA_NOC,CANADA_URL
from app.ca_province_wages import bulk_rows

DATASETS={'2025':2025}
CATALOGUE='https://open.canada.ca/data/api/action/package_show?id=adad580f-76b0-4502-bd05-20c125de9116'
LICENCE='https://open.canada.ca/en/open-government-licence-canada'
REGISTRY=Path(__file__).resolve().parents[1]/'data/job_bank_2025_geographies.json'


def validate_catalogue(path):
    data=json.loads(Path(path).read_text())
    result=data.get('result',{})
    if data.get('success') is not True or result.get('license_id')!='ca-ogl-lgo' or result.get('license_url')!=LICENCE:
        raise ValueError('Unverified Job Bank licence')
    if not any(r.get('id')=='9da94d63-b178-4a64-aeb3-b6a3bd721ad2' and r.get('url')==CANADA_URL and r.get('format','').upper()=='CSV' for r in result.get('resources',[])):
        raise ValueError('Unverified resource URL/layout')
    return result['metadata_modified']


def observations(path,stats):
    registry=json.loads(REGISTRY.read_text())['geographies']
    by_code={}
    for job,(code,title) in CANADA_NOC.items():by_code.setdefault('NOC_'+code,[]).append((job,title))
    stats.update(source_rows=0,selected_rows=0,excluded_rows=0,missing_wages=0)
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        for row,geo,unit,values in bulk_rows(stream,registry):
            stats['source_rows']+=1;code=row['NOC_CNP'].strip()
            if code not in by_code:stats['excluded_rows']+=1;continue
            jobs=by_code[code]
            if any(not row['NOC_Title_eng'].strip().casefold().startswith(title.casefold()) for _,title in jobs):
                raise ValueError('NOC title drift')
            stats['selected_rows']+=1
            for measure,value in values.items():
                if value is None:stats['missing_wages']+=1
                yield {'provider':'job_bank','dataset':'JobBank2025','country':'CA','geography':geo,
                    'geography_name':row['ER_Name'],'original_geography':row['ER_Code_Code_RE'],
                    'original_province':row['prov'],'indicator':'occupational_salary',
                    'classification':'NOC2021:'+code.removeprefix('NOC_'),
                    'original_occupation_title':row['NOC_Title_eng'],'occupations':[job for job,_ in jobs],'measure':measure,'unit':unit,'currency':'CAD',
                    'period':'unknown' if row['Reference_Period']=='NA' else row['Reference_Period'],
                    'original_period':row['Reference_Period'],'value':value,
                    'source_url':CANADA_URL,'original_data_source':row['Data_Source_E'],
                    'revision_date':row['Revision_Date_Date_revision'],'licence_url':LICENCE,
                    'flags':'unavailable' if value is None else '',
                    'dimensions':{'classification_version':'NOC2021'}}


def run(store,downloader,name,ttl=0):
    if name not in DATASETS:raise ValueError('Unverified release')
    run_id=store.start('job_bank',name);stats={}
    try:
        meta,meta_artifact=downloader.get(CATALOGUE,ttl=ttl)
        modified=validate_catalogue(meta);store.artifact(meta_artifact)
        path,artifact=downloader.get(CANADA_URL,ttl=ttl);store.artifact(artifact)
        counts=store.ingest('job_bank:'+name,artifact['sha256'],observations(path,stats),batch_size=1000)
        result={**counts,**stats,'acquisition_mode':'live_bulk','source_url':CANADA_URL,
                'destination_host':'opencanada.blob.core.windows.net','licence_url':LICENCE,
                'catalogue_modified_at':modified,'acquired_at':artifact['fetched_at'],
                'artifact_sha256':artifact['sha256']}
        store.finish(run_id,'complete',result=result);return result
    except Exception as error:
        store.finish(run_id,'failed',type(error).__name__,result=stats);raise

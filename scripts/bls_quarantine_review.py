"""Read-only complete BLS quarantine review; this tool cannot approve data.

Magnitude compares the nearest *earlier* finite source observation with identical
series dimensions, including quarantined values. This is a retrospective metric,
not a claim to reconstruct the original ingestion comparator.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3


def review(path, sample_limit=32):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Explicit regular staging file required')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    groups=Counter(); dimensions={k:Counter() for k in ('year','classification','geographic_level','measure','reason','magnitude')}
    sample={}; count=0; low_adjacent=0; sources={}
    try:
        for key,series,payload,reason in db.execute("SELECT key,series_key,payload,reason FROM bulk_versions WHERE status='quarantined' AND json_extract(payload,'$.provider')='bls' ORDER BY key,version"):
            row=json.loads(payload); count+=1
            previous=db.execute("""SELECT payload FROM bulk_versions WHERE series_key=? AND key!=?
                AND status IN ('accepted','quarantined') AND value!=''
                AND json_extract(payload,'$.period')<?
                ORDER BY json_extract(payload,'$.period') DESC, imported_at DESC LIMIT 1""",(series,key,row['period'])).fetchone()
            old=json.loads(previous[0]) if previous else None
            delta=None
            if old and Decimal(old['value'])!=0:delta=abs(Decimal(row['value'])/Decimal(old['value'])-1)*100
            band=('no_prior_comparable' if delta is None else
                  '0_to_30_percent' if delta<=30 else
                  'over_30_to_50_percent' if delta<=50 else
                  'over_50_to_100_percent' if delta<=100 else 'over_100_percent')
            if delta is not None and delta<=30:low_adjacent+=1
            level='national' if row['geography']=='national' else 'BLS_area_type_'+row['original_area_type']
            vals=(row['period'],row['classification'],level,row['measure']+':'+row['unit'],reason,band)
            groups[vals]+=1
            for dimension,val in zip(dimensions,vals):dimensions[dimension][val]+=1
            sources[row['artifact_sha256']]=row['source_url']
            item={'key':key,'period':row['period'],'classification':row['classification'],
                  'geography':row['geography'],'geography_name':row['geography_name'],
                  'measure':row['measure'],'unit':row['unit'],'value':row['value'],
                  'previous_period':old['period'] if old else None,'previous_value':old['value'] if old else None,
                  'absolute_variation_percent':str(delta.quantize(Decimal('.0001'))) if delta is not None else None,
                  'magnitude_band':band,'reason':reason,'artifact_sha256':row['artifact_sha256'],
                  'source_url':row['source_url'],'source_member':row['source_member'],
                  'original_salary_token':row['original_salary_token'],'decision':'remain_quarantined'}
            # Stratified extremes: all measure/unit pairs, year/geo pairs and
            # magnitude bands; descriptive review sample, not a random sample.
            for bucket in (('measure',row['measure'],row['unit']),('year_geo',row['period'],level),('magnitude',band)):
                if bucket not in sample or (delta or Decimal(0))>Decimal(sample[bucket]['absolute_variation_percent'] or 0):sample[bucket]=item
        representatives={}
        for bucket in sorted(sample):representatives.setdefault(sample[bucket]['key'],sample[bucket])
        return {'schema':'earnwage-bls-quarantine-review-v1','quarantined_observations':count,
                'approved_by_review':0,'decision':'all_remain_quarantined',
                'metric':'nearest earlier finite source observation, same complete series dimensions; retrospective, not original comparator',
                'at_or_below_generic_threshold_against_nearest_prior':low_adjacent,
                'dimensions':{k:dict(sorted(v.items())) for k,v in dimensions.items()},
                'groups':[dict(zip(dimensions,k),count=v) for k,v in sorted(groups.items())],
                'artifacts':sources,'sample_method':'maximum variation per measure/unit, year/geographic level and magnitude band; not a statistical random sample',
                'sample':list(representatives.values())[:sample_limit]}
    finally:db.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--staging',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=review(args.staging)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k] for k in ('quarantined_observations','approved_by_review','at_or_below_generic_threshold_against_nearest_prior','dimensions')}))

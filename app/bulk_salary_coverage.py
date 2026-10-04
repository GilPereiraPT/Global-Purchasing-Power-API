"""Streaming salary coverage aggregation for explicit offline staging databases."""
import json
from collections import Counter,defaultdict
from pathlib import Path
from decimal import Decimal
from app.bulk_core import observation_key
from app.bulk_inventory_export import read_inventory,numeric
from app.bulk_coverage import readonly
from app.us_oews import WAGE_FIELDS
from app.north_america import CANADA_URL,US_SOC


def baseline_index(directory, *, normalized=None):
    """Only snapshots with reconstructible official observation identities count.

    ``normalized`` optionally collects the same source-qualified rows by key for
    an explicitly authorized raw-table export. The caller validates provenance
    and completeness first; this function does not assert production scope.
    """
    index={};pairs=set();files=[]
    def add(r):
        key=observation_key(r);value=numeric(r['value'])
        if key in index and index[key]!=value:raise ValueError('Conflicting baseline aliases')
        index[key]=value
        if normalized is not None:normalized[key]=r
    for name in ('us_oews_curated.json','north_america_wages.json','ca_province_wages.json'):
        path=Path(directory)/name
        if not path.exists():continue
        files.append(name);data=json.loads(path.read_text())
        for row in data.get('records',[]):
            if name=='us_oews_curated.json':
                if row['o_group']!='detailed' or str(row['naics'])!='000000' or str(row['own_code'])!='1235':continue
                jobs=[j for j,(code,_) in US_SOC.items() if code==row['occ_code']]
                if not jobs:continue
                pairs.update(('US',j) for j in jobs)
                for f in WAGE_FIELDS:
                    if row.get(f.lower()) is None:continue
                    add(dict(provider='bls',dataset='OEWS',country='US',
                        geography='national' if str(row['area_type'])=='1' else f"BLS:{row['area_type']}:{row['area']}",
                        indicator='occupational_salary',classification='SOC2018:'+row['occ_code'],
                        measure=f[2:].lower(),unit='USD/hour' if f.startswith('H_') else 'USD/year',currency='USD',
                        period=str(row['published_year']),value=row[f.lower()],
                        dimensions={'industry':'000000','ownership':'1235','occupation_group':'detailed'}))
            elif row.get('country','CA')=='CA' and row.get('source_url')==CANADA_URL and str(row.get('classification','')).startswith('NOC2021:'):
                pairs.add(('CA',row['occupation']))
                geo='CA:province:'+row['province'] if 'province' in row else row['geography']
                add(dict(provider='job_bank',dataset='JobBank2025',country='CA',geography=geo,
                         indicator='occupational_salary',classification=row['classification'],measure=row['measure'],
                         unit=row['unit'],currency='CAD',period=row['reference_period'],value=row['value'],
                         dimensions={'classification_version':'NOC2021'}))
    return index,pairs,files


def summarize(paths,snapshot_dir,inventory=None,authorization=None):
    baseline,baseline_pairs,files=baseline_index(snapshot_dir)
    prod_meta,prod_index=read_inventory(inventory,authorization=authorization) if inventory else ({},{})
    sources={};details=defaultdict(lambda:dict(observations=0,periods=set(),geographies=set(),historical_observations=0))
    seen=set();pairs=set();prod_counts=Counter();baseline_counts=Counter();incomplete=0
    for path in paths:
        with readonly(path) as db:
            runs=[dict(zip(('provider','dataset','status','acquisition_mode'),r)) for r in db.execute("SELECT r.provider,r.dataset,r.status,COALESCE(json_extract(d.result,'$.acquisition_mode'),'unverified_staging') FROM bulk_runs r LEFT JOIN bulk_run_results d ON d.run_id=r.id ORDER BY r.id")]
            for raw, in db.execute("SELECT payload FROM bulk_current WHERE json_extract(payload,'$.provider') IN ('bls','job_bank')"):
                row=json.loads(raw)
                release=row['period'] if row['provider']=='bls' else '2025'
                matching=[r for r in runs if r['provider']==row['provider'] and r['dataset']==release]
                if not matching or matching[-1]['status']!='complete':
                    incomplete+=1;continue
                key=observation_key(row)
                if key in seen:raise ValueError('Overlapping staging identities; select disjoint files')
                seen.add(key);provider=row['provider'];value=numeric(row['value'])
                source=sources.setdefault(provider,dict(accepted=0,quarantined_versions=0,missing_versions=0,
                     national=0,regional=0,new_regional_observations=0,new_historical_observations=0,baseline_differences=Counter(),by_period=Counter(),by_geography_type=Counter(),sources=set(),acquisition_dates=set(),acquisition_modes=set(),runs=[]))
                source['acquisition_modes'].add(matching[-1]['acquisition_mode'])
                source['accepted']+=1;source['national' if row['geography']=='national' else 'regional']+=1
                source['by_period'][row['period']]+=1
                geo=row['geography'];kind='national' if geo=='national' else geo.split(':')[1]
                source['by_geography_type'][kind]+=1;source['sources'].add(row['source_url'])
                diff='new' if key not in baseline else 'duplicates' if value==baseline[key] else 'revisions'
                baseline_counts[diff]+=1;source['baseline_differences'][diff]+=1
                if diff=='new' and row['geography']!='national':source['new_regional_observations']+=1
                if diff=='new' and row['period'].isdigit() and len(row['period'])==4 and row['period']<'2025':source['new_historical_observations']+=1
                if inventory:
                    prod_counts['new' if key not in prod_index else 'duplicates' if value==prod_index[key] else 'revisions']+=1
                for job in row['occupations']:
                    pair=(row['country'],job);pairs.add(pair);item=details[pair]
                    item['observations']+=1;item['periods'].add(row['period']);item['geographies'].add(geo)
                    if provider=='bls' and row['period']<'2025' and key not in baseline:item['historical_observations']+=1
            for provider,status,count in db.execute("SELECT json_extract(payload,'$.provider'),status,COUNT(*) FROM bulk_versions WHERE status IN ('missing','quarantined') GROUP BY 1,2"):
                if provider in sources:sources[provider]['missing_versions' if status=='missing' else 'quarantined_versions']+=count
            for raw, in db.execute('SELECT metadata FROM bulk_artifacts'):
                artifact=json.loads(raw)
                for source in sources.values():
                    if artifact['url'] in source['sources'] and artifact.get('fetched_at'):source['acquisition_dates'].add(artifact['fetched_at'])
            for provider,source in sources.items():source['runs'].extend(r for r in runs if r['provider']==provider)
    def clean(value):
        if isinstance(value,set):return sorted(value)
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
        return value
    return clean({'scope':'explicit offline staging; no production database access',
        'excluded_incomplete_run_observations':incomplete,'sources':sources,'newly_covered_pairs':[{'country':c,'occupation':j} for c,j in sorted(pairs-baseline_pairs)],
        'covered_pairs':len(pairs),'baseline_pairs':len(baseline_pairs),'baseline_files':files,
        'baseline_not_in_accepted':len(set(baseline)-seen),
        'baseline_observation_differences':{k:baseline_counts[k] for k in ('new','revisions','duplicates')},
        'production_inventory':{'status':'compared','scope':prod_meta['scope'],'exported_at':prod_meta['exported_at'],**{k:prod_counts[k] for k in ('new','revisions','duplicates')}} if inventory else {'status':'not_provided','new':None,'revisions':None,'duplicates':None},
        'occupations':[{'country':c,'occupation':j,**v} for (c,j),v in sorted(details.items())],
        'baseline_note':'Differences only against reconstructible committed official snapshots; not actual production coverage.',
        'acquisition_mode':'live_bulk only for complete runs; failed/running runs are explicitly listed; fixtures are not acquisition evidence'})


def attach(report,summary):
    report['bulk_salary_coverage']=summary
    for country in report['countries']:
        for item in country['occupations']:
            bulk=next((r for r in summary['occupations'] if r['country']==country['country'] and r['occupation']==item['occupation']),None)
            if not bulk:continue
            item['bulk_observations']=bulk['observations'];item['bulk_periods']=bulk['periods'];item['bulk_geographies']=bulk['geographies']
            provider='bls' if country['country']=='US' else 'job_bank'
            item['status']='offline_bulk_verified' if summary['sources'][provider]['acquisition_modes']==['live_bulk'] else 'offline_bulk_sample_or_unverified'
            item['stored_observations']+=bulk['observations']
            item['original_periods']=sorted(set(item['original_periods'])|set(bulk['periods']))
            item['missing_target_years']=[y for y in item['missing_target_years'] if str(y) not in bulk['periods']]
            if country['country']=='CA':
                covered={g.removeprefix('CA:province:') for g in bulk['geographies'] if g.startswith('CA:province:')}
                item['missing_configured_regions_in_db']=[g for g in item['missing_configured_regions_in_db'] if g not in covered]
            elif country['country']=='US':
                item['missing_configured_regions_in_db']=[]
                item['regional_identifier_note']='Original BLS FIPS/MSA/nonmetro identifiers preserved in bulk_geographies; configured ISO selectors not assumed equivalent.'
            item['regional_status']='offline_bulk_regions' if any(g!='national' for g in bulk['geographies']) else item['regional_status']
    report['summary']['bulk_physical_salary_observations']=sum(s['accepted'] for s in summary['sources'].values())
    report['summary']['pairs_with_stored_observations']=sum(o['stored_observations']>0 for c in report['countries'] for o in c['occupations'])
    return report

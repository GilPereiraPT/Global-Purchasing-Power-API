"""One paginated WDI request per indicator, all catalogue countries/history.

No country-by-occupation requests, null interpolation or WHO/WDI splicing.
Only WDI source 2, the existing indicator identifiers and published annual rows.
"""
import json
import math
from decimal import Decimal
from urllib.parse import urlencode

from app.country_insights import ISO3, INDICATORS

COUNTRIES = {v:k for k,v in ISO3.items()}
PER_PAGE = 10000
MAX_PAGES = 100


def url(name,page=1):
    if name not in INDICATORS or isinstance(page,bool) or not 1<=page<=MAX_PAGES:
        raise ValueError('Invalid WDI selection')
    return ('https://api.worldbank.org/v2/country/' + ';'.join(ISO3.values()) +
            '/indicator/' + INDICATORS[name][0] + '?' + urlencode(
                {'format':'json','source':2,'per_page':PER_PAGE,'page':page}))


def integer(value,name):
    if isinstance(value,bool) or not str(value).isdigit():raise ValueError('Invalid WDI '+name)
    return int(value)


def parse(path,name,requested_page,seen_rows=None,missing_registry=None):
    with open(path,encoding='utf-8-sig') as f:
        payload=json.load(f,parse_float=Decimal)
    if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[0],dict) or not isinstance(payload[1],list):
        raise ValueError('Invalid WDI JSON schema')
    metadata,rawrows=payload
    page=integer(metadata.get('page'),'page')
    pages=integer(metadata.get('pages'),'pages')
    total=integer(metadata.get('total'),'total')
    per_page=integer(metadata.get('per_page'),'per_page')
    if (page!=requested_page or not 1<=pages<=MAX_PAGES or page>pages or per_page!=PER_PAGE
            or pages!=max(1,math.ceil(total/per_page)) or str(metadata.get('sourceid'))!='2'):
        raise ValueError('Inconsistent WDI pagination/source')
    expected=min(per_page,max(0,total-(page-1)*per_page))
    if len(rawrows)!=expected:raise ValueError('Truncated WDI page')
    rows=[]
    missing=0
    code,unit=INDICATORS[name]
    seen=seen_rows if seen_rows is not None else set()
    for item in rawrows:
        if not isinstance(item,dict) or not isinstance(item.get('indicator'),dict) or not isinstance(item.get('country'),dict):
            raise ValueError('Invalid WDI row schema')
        iso3=item.get('countryiso3code')
        country=COUNTRIES.get(iso3)
        if country is None or item['country'].get('id')!=country or item['indicator'].get('id')!=code:
            raise ValueError('Unexpected WDI country or indicator')
        period=str(item.get('date'))
        if len(period)!=4 or not period.isascii() or not period.isdigit() or not 1960<=int(period)<=2100:
            raise ValueError('Unexpected WDI period')
        if (country,period) in seen:raise ValueError('Duplicate WDI observation')
        seen.add((country,period))
        if item.get('unit','') not in ('',unit):raise ValueError('Unexpected WDI unit')
        if item.get('obs_status','') not in ('','F'):
            # Unknown publication statuses need review, not conversion to a wage.
            raise ValueError('Unverified WDI observation status')
        value=item.get('value')
        if value is None:
            missing+=1
            if missing_registry is not None:missing_registry.setdefault(country,[]).append(period)
            continue
        if isinstance(value,bool) or not isinstance(value,(int,Decimal)):
            raise ValueError('Invalid WDI value')
        value=Decimal(value)
        if not value.is_finite() or abs(value)>Decimal('1e12'):
            raise ValueError('Non-finite or out-of-range WDI value')
        if name!='inflation_annual' and value<0:raise ValueError('Negative WDI indicator')
        bounded=('gini','health_coverage','electricity_access','safe_drinking_water',
                 'safe_sanitation','internet_use','unemployment','youth_unemployment',
                 'employment_population_ratio','adult_literacy','advanced_education_unemployment',
                 'out_of_pocket_health_expenditure','political_stability','rule_of_law',
                 'control_of_corruption','bribery_incidence_firms','tax_official_gifts_firms')
        if name in bounded and value>100:raise ValueError('WDI indicator exceeds 0-100 scale')
        rows.append({'provider':'world_bank','dataset':'WDI:2:'+code,'country':country,
                     'geography':'national','indicator':name,'classification':None,
                     'measure':'published_annual_indicator','unit':unit,'currency':None,
                     'period':period,'value':str(value),'source_url':url(name,page),
                     'flags':item.get('obs_status',''),'publication_version':metadata.get('lastupdated'),
                     'original_indicator_code':code,'original_country_code':iso3})
    rows.sort(key=lambda row:(row['country'],row['period']))
    return metadata,rows,missing


def run(store,downloader,name,ttl=0):
    run_id=store.start('world_bank',name)
    totals={'accepted':0,'quarantined':0,'duplicates':0,'resumed_rows':0,'missing':0,'pages':0}
    reference=None
    seen=set()
    missing_periods={}
    try:
        for page in range(1,MAX_PAGES+1):
            path,artifact=downloader.get(url(name,page),ttl=ttl)
            metadata,rows,missing=parse(path,name,page,seen_rows=seen,missing_registry=missing_periods)
            identity=tuple(str(metadata.get(k)) for k in ('pages','total','per_page','sourceid','lastupdated'))
            if reference is not None and reference!=identity:raise ValueError('WDI release changed during pagination')
            reference=identity
            store.artifact(artifact)
            counts=store.ingest('world_bank:'+name+':'+str(page),artifact['sha256'],rows)
            for k,v in counts.items():totals[k]+=v
            totals['missing']+=missing
            totals['pages']+=1
            if page==integer(metadata['pages'],'pages'):break
        result={**totals,'missing_periods_by_country':missing_periods}
        store.finish(run_id,'complete',result=result)
        return result
    except Exception as error:
        store.finish(run_id,'failed',type(error).__name__)
        raise

"""Strict streaming Eurostat full-dataset TSV gzip connector.

Only exact existing dimension selections are admitted. Groups and unrelated
categories are ignored, never substituted; unknown dimensions fail closed.
GB CPI/earnings use other providers in existing APIs, so never project Eurostat
GB equivalents into those ONS/OECD series.
"""
import csv
import gzip
import io
import re
from decimal import Decimal, InvalidOperation

from app.eurostat_economy import SERIES, EUROSTAT_COUNTRIES

MAX_EXPANDED = 256*1024*1024
GEO = {('UK' if c=='GB' else c):c for c in EUROSTAT_COUNTRIES}
FLAGS = {'b','c','d','e','f','i','n','p','r','s','u','z'}


def url(name):
    if name not in SERIES:raise ValueError('Unknown Eurostat series')
    return ('https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/' +
            SERIES[name]['dataset']+'?format=TSV&compressed=true')


class BoundedReader(io.RawIOBase):
    def __init__(self,stream,limit):self.stream,self.remaining=stream,limit
    def readable(self):return True
    def readinto(self,buffer):
        data=self.stream.read(min(len(buffer),self.remaining+1))
        self.remaining-=len(data)
        if self.remaining<0:raise ValueError('Expanded TSV exceeds configured size')
        buffer[:len(data)]=data
        return len(data)


def period(value,frequency):
    if frequency=='annual':
        return bool(re.fullmatch(r'(19|20)\d{2}',value))
    return bool(re.fullmatch(r'(19|20)\d{2}(?:M|-)(0[1-9]|1[0-2])',value))


def parse(path,name,counters=None,max_expanded=MAX_EXPANDED):
    spec=SERIES[name]
    stats=counters if counters is not None else {}
    for k in ('selected','missing','excluded_dimensions','flagged'):
        stats.setdefault(k,0)
    stats.setdefault('missing_periods_by_country',{})
    with open(path,'rb') as raw:
        if raw.read(2)!=b'\x1f\x8b':raise ValueError('Expected gzip TSV signature')
        raw.seek(0)
        with gzip.GzipFile(fileobj=raw) as gz:
            with io.TextIOWrapper(io.BufferedReader(BoundedReader(gz,max_expanded)),encoding='utf-8-sig',newline='') as text:
                reader=csv.reader(text,delimiter='\t')
                header=next(reader,[])
                if not header or '\\TIME_PERIOD' not in header[0]:raise ValueError('Invalid Eurostat TSV header')
                dimension_text,separator,tail=header[0].partition('\\TIME_PERIOD')
                dims=dimension_text.split(',')
                if tail.strip() or set(dims)!={'geo',*spec['filters']} or len(dims)!=len(set(dims)):
                    raise ValueError('Unexpected Eurostat TSV dimensions')
                periods=[p.strip() for p in header[1:]]
                if not periods or len(set(periods))!=len(periods) or any(not period(p,spec['frequency']) for p in periods):
                    raise ValueError('Invalid/duplicate Eurostat periods')
                selected=set()
                for row in reader:
                    if not row or len(row)!=len(header):raise ValueError('Truncated Eurostat TSV row')
                    codes=row[0].split(',')
                    if len(codes)!=len(dims):raise ValueError('Invalid Eurostat dimension codes')
                    dimensions=dict(zip(dims,codes))
                    country=GEO.get(dimensions['geo'])
                    if country is None or any(dimensions[k]!=v for k,v in spec['filters'].items()):
                        stats['excluded_dimensions']+=1
                        continue
                    if country=='GB' and name!='household_price_level_eu27':
                        stats['excluded_dimensions']+=1
                        continue
                    if country in selected:raise ValueError('Duplicate selected Eurostat dimension tuple')
                    selected.add(country)
                    for p,cell in zip(periods,row[1:]):
                        parts=cell.strip().split()
                        if not parts:raise ValueError('Empty TSV cell; missing must be explicit')
                        flags=''.join(parts[1:])
                        if any(f not in FLAGS for f in flags):raise ValueError('Unknown Eurostat observation flag')
                        if parts[0]==':':
                            stats['missing']+=1
                            stats['missing_periods_by_country'].setdefault(country,[]).append({'period':p,'flags':flags})
                            continue
                        # c = confidential, even if an unexpected numeric value exists.
                        if 'c' in flags:
                            stats['missing']+=1
                            stats['missing_periods_by_country'].setdefault(country,[]).append({'period':p,'flags':flags})
                            continue
                        try:value=Decimal(parts[0])
                        except InvalidOperation:raise ValueError('Invalid Eurostat value') from None
                        if not value.is_finite() or abs(value)>Decimal('1e12'):
                            raise ValueError('Invalid/out-of-range Eurostat value')
                        if name!='hicp_annual_change_monthly' and value<0:raise ValueError('Negative Eurostat index/earnings')
                        stats['selected']+=1
                        if flags:stats['flagged']+=1
                        normalized=p.replace('M','-') if spec['frequency']=='monthly' else p
                        yield {'provider':'eurostat','dataset':spec['dataset'],'country':country,
                               'geography':'national','indicator':name,'classification':None,
                               'measure':'statistical_reference' if name=='net_annual_earnings_reference' else 'published_indicator',
                               'unit':spec['unit'],'currency':'EUR' if name=='net_annual_earnings_reference' else None,
                               'period':normalized,'value':str(value),'source_url':url(name),
                               'flags':flags,'original_dimensions':dimensions,'original_period':p}
                if not selected:
                    raise ValueError('No verified country/dimension selection in complete TSV')


def run(store,downloader,name,ttl=0):
    run_id=store.start('eurostat',name)
    counters={}
    try:
        path,artifact=downloader.get(url(name),ttl=ttl)
        store.artifact(artifact)
        counts=store.ingest('eurostat:'+name,artifact['sha256'],parse(path,name,counters))
        result={**counts,**counters}
        store.finish(run_id,'complete',result=result)
        return result
    except Exception as error:
        store.finish(run_id,'failed',type(error).__name__)
        raise

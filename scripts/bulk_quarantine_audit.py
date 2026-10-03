"""Reproducible read-only audit of every quarantined staging version."""
import argparse
import csv
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path
from app.bulk_core import observation_key


def audit(staging,output):
    if not Path(staging).is_file():raise ValueError('Explicit staging required')
    with sqlite3.connect(Path(staging).resolve().as_uri()+'?mode=ro',uri=True) as db:
        rows=[(json.loads(p),status,reason) for p,status,reason in db.execute('SELECT payload,status,reason FROM bulk_versions')]
    series={}
    for r,status,reason in rows:
        if r['value'] is not None:series.setdefault(observation_key(r,series=True),[]).append(r)
    results=[]
    for r,status,reason in rows:
        if status!='quarantined':continue
        candidates=[p for p in series[observation_key(r,series=True)] if p['period']!=r['period']]
        prior=[p for p in candidates if p['period']<r['period']]
        near=max(prior,key=lambda p:p['period']) if prior else min(candidates,key=lambda p:p['period']) if candidates else None
        delta=None;relative=None
        if near:
            old=Decimal(str(near['value']));delta=Decimal(str(r['value']))-old
            if old:relative=abs(delta/old)
        cause='methodology_break' if 'b' in r['flags'] else 'provider_flag' if reason=='provider_quality_or_methodology_flag' else 'numerical_variation'
        results.append({'provider':r['provider'],'dataset':r['dataset'],'country':r['country'],
                        'indicator':r['indicator'],'period':r['period'],'value':r['value'],
                        'flags':r['flags'],'cause':cause,'ledger_reason':reason,
                        'comparison_period':near['period'] if near else '',
                        'comparison_value':near['value'] if near else '',
                        'absolute_delta':str(delta) if delta is not None else '',
                        'relative_delta':str(relative) if relative is not None else '',
                        'manual_assessment':'required','disposition':'retain_quarantine',
                        'source_url':r['source_url'],'artifact_sha256':r['artifact_sha256']})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]) if results else ['cause']);w.writeheader();w.writerows(results)
    return {'reviewed':len(results),'causes':dict(Counter(r['cause'] for r in results)),
            'manual_assessment_required':len(results),'automatically_approved':0,
            'note':'Adjacent source values provide review context, not independent validation or automatic acceptance.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--staging',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(audit(a.staging,a.output)))

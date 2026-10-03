"""Offline WDI/Eurostat worker, independent of production API and Data Manager.

Requires an explicit private working directory. Never uses production DB env vars.
Reports/ledger persist on failure; exit nonzero if any selected import fails.
"""
import argparse
import json
import os
import sys
import fcntl
from contextlib import contextmanager
from pathlib import Path

from app.bulk_core import BulkStore, Downloader
from app.bulk_schedule import load, due
from app.country_insights import INDICATORS
from app.eurostat_economy import SERIES
from app import bulk_world_bank, bulk_eurostat, bulk_bls, bulk_job_bank


def safe_workspace(directory):
    root=Path(directory).expanduser().resolve()
    if 'public_html' in root.parts:raise ValueError('Use a private offline workspace')
    for name in ('EARNWAGE_INSIGHTS_DB','GPP_CACHE_DB'):
        configured=os.environ.get(name)
        if configured and (root==Path(configured).resolve().parent or root in Path(configured).resolve().parents):
            raise ValueError('Workspace overlaps a configured application database')
    root.mkdir(parents=True,exist_ok=True)
    for child in ('staging.sqlite3','cache','acquisition.json','acquisition.md','.bulk-worker.lock'):
        target=root/child
        if target.is_symlink():raise ValueError('Workspace paths must not be symlinks')
    return root


def report_markdown(report):
    lines=['# Relatório de aquisição offline','',
        f"Observações aceites no staging: {report['accepted_observations']}",
        f"Versões em quarentena: {report['quarantined_versions']}",
        '', '| Fonte | Dataset | Estado | Antes | Depois | Erro |',
        '| --- | --- | --- | ---: | ---: | --- |']
    for r in report['runs']:
        lines.append(f"| {r['provider']} | {r['dataset']} | {r['status']} | {r['before_count']} | {r['after_count']} | {r['error_type'] or ''} |")
    lines.extend(['','Contagens são locais. Dados sintéticos de testes não são aquisição oficial.',
                  'Falhas não eliminam dados anteriores. Staging não atualiza produção.'])
    return '\n'.join(lines)+'\n'


@contextmanager
def exclusive_worker(root):
    with (root/'.bulk-worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another offline worker is running in this workspace') from None
        try:
            yield
        finally:
            fcntl.flock(lock,fcntl.LOCK_UN)


def execute(workspace,provider,names,downloader=None,policy_path=None,only_due=False,cache_ttl=3600):
    registry={'world_bank':(bulk_world_bank,INDICATORS),'eurostat':(bulk_eurostat,SERIES),'bls':(bulk_bls,bulk_bls.DATASETS),'job_bank':(bulk_job_bank,bulk_job_bank.DATASETS)}
    if provider not in registry:raise ValueError('Unknown bulk provider')
    module,choices=registry[provider]
    if not names or len(names)>4 or len(set(names))!=len(names) or any(n not in choices for n in names):
        raise ValueError('Choose one to four distinct registered datasets')
    root=safe_workspace(workspace)
    with exclusive_worker(root):
        return _execute_locked(root,module,provider,names,downloader,policy_path,only_due,cache_ttl)


def _execute_locked(root,module,provider,names,downloader,policy_path,only_due,cache_ttl):
    policy=load(policy_path) if policy_path else load()
    store=BulkStore(root/'staging.sqlite3')
    owned=downloader is None
    fetch=downloader or Downloader(root/'cache')
    failed=False
    results=[]
    try:
        for name in names:
            specific=policy.get('series_overrides',{}).get(provider+':'+name)
            effective={**policy,'providers':{**policy['providers'],provider:specific or policy['providers'][provider]}}
            if only_due and not due(store,provider,name,effective):
                results.append({'dataset':name,'status':'not_due'})
                continue
            try:
                counts=module.run(store,fetch,name,ttl=cache_ttl)
                results.append({'dataset':name,'status':'complete',**counts})
            except Exception as error:
                # No exception messages/headers/credential values in user-facing logs.
                results.append({'dataset':name,'status':'failed','error_type':type(error).__name__})
                failed=True
        report={**store.report(),'last_invocation':results,
                'scope':'offline staging only; no production database writes',
                'source_validation':'Schema/provenance validation; live provider contract requires successful download',
                'publication_schedule':'Intervals plus conditional HTTP; precise release calendars not connected'}
        (root/'acquisition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (root/'acquisition.md').write_text(report_markdown(report))
        return (1 if failed else 0),report
    finally:
        store.close()
        if owned:fetch.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--provider',choices=('world_bank','eurostat','bls','job_bank'),required=True)
    parser.add_argument('--dataset',action='append',required=True)
    parser.add_argument('--policy',type=Path)
    parser.add_argument('--due',action='store_true')
    parser.add_argument('--recheck',action='store_true',help='Bypass one-hour freshness cache and revalidate upstream')
    a=parser.parse_args()
    code,report=execute(a.workspace,a.provider,a.dataset,policy_path=a.policy,only_due=a.due,cache_ttl=0 if a.recheck else 3600)
    print(json.dumps({'accepted_observations':report['accepted_observations'],
                      'quarantined_versions':report['quarantined_versions'],
                      'results':report['last_invocation']}))
    return code

if __name__=='__main__':
    sys.exit(main())

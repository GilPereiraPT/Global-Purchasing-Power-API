"""Offline coverage report: explicit read-only DBs and committed snapshots.

No schema creation, network or production-environment database discovery.
Missing target years are gaps in this inventory, not proof of upstream absence.
"""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app.client_config import REGIONS
from app.bulk_classifications import catalogue as classification_catalogue
from app.country_insights import INDICATORS
from app.bulk_catalogue import catalogue
from app.occupation_source_audits import source_audit

ROOT = Path(__file__).resolve().parent.parent
TABLES = ('salary_observations','north_america_wages','pt_occupation_wages',
          'uk_ashe_wages','de_entgeltatlas_wages','fr_insee_wages','nl_cbs_wages',
          'ca_province_wages','br_rais_state_wages','de_entgeltatlas_state_wages','us_oews')
DEFAULT_COUNTRIES = {'ca_province_wages':'CA','ca_statcan_groups':'CA',
                     'br_rais_2025_states':'BR','in_plfs_2025_nco':'IN',
                     'es_ine_eaes_28186':'ES','us_oews_curated':'US'}


def readonly(path):
    path = Path(path).resolve(strict=True)
    return sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)


def normalized_rows(row):
    if 'occ_code' not in row:
        yield row
        return
    from app.north_america import US_SOC
    if row.get('o_group')!='detailed' or str(row.get('naics'))!='000000' or str(row.get('own_code'))!='1235':
        yield {**row,'country':'US','precision':'unmapped_or_non_comparable_oews_scope'}
        return
    for occupation,(code,title) in US_SOC.items():
        if code==row['occ_code']:
            geo='national' if str(row.get('area_type'))=='1' else row.get('prim_state') if str(row.get('area_type'))=='2' else 'area:'+str(row.get('area'))
            yield {**row,'country':'US','occupation':occupation,'classification':'SOC2018:'+code,
                   'geography':geo,'precision':'existing_approved_detailed_soc_mapping',
                   'measure':'published_mean_and_median_hourly_and_annual',
                   'unit':'USD/hour_and_USD/year_preserved_separately'}


def database_rows(path):
    if path is None:
        return [], {}, []
    rows, economic, failures = [], {}, []
    with readonly(path) as db:
        db.row_factory = sqlite3.Row
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in TABLES:
            if table in tables:
                for r in db.execute('SELECT * FROM ' + table):
                    rows.extend(normalized_rows(dict(r, origin='database', table=table)))
        for table, period in (('observations','year'),('eurostat_observations','period')):
            if table in tables:
                for r in db.execute('SELECT country,indicator,' + period + ' FROM ' + table):
                    economic.setdefault((r[0], table, r[1]), set()).add(str(r[2]))
        for table, status in (('refresh_log','status'),('eurostat_refresh','status')):
            if table in tables:
                for r in db.execute('SELECT * FROM ' + table + " WHERE " + status + " != 'available'"):
                    failures.append(dict(r, table=table))
    return rows, economic, failures


def snapshots(directory):
    files, rows = [], []
    for path in sorted(Path(directory).glob('*.json')):
        raw = path.read_bytes()
        obj = json.loads(raw)
        metadata = obj if isinstance(obj, dict) else {}
        items = (obj if isinstance(obj,list) else next((obj[k] for k in
                 ('records','observations','rows') if isinstance(obj.get(k),list)), []))
        files.append({'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
                      'records':len(items),'provenance_status':'committed_snapshot_not_new_upstream_validation',
                      'source':metadata.get('source'),'licence':metadata.get('licence', metadata.get('reuse_license'))})
        for item in items:
            if not isinstance(item, dict):
                continue
            row = {**{k:v for k,v in metadata.items() if not isinstance(v,(dict,list))}, **item}
            row.setdefault('country', DEFAULT_COUNTRIES.get(path.stem))
            row.update(origin='snapshot', file=path.name)
            rows.extend(normalized_rows(row))
    return files, rows


def period(row):
    return str(row.get('reference_period',row.get('period','')))


def geography(row):
    # Original IDs are preserved. No city inferred from national data.
    return str(row.get('geography',row.get('province',row.get('uf',row.get('state',row.get('state_code','unknown'))))))


def classification(row):
    for key in ('classification','pcs_ese','brc_code','cbo_code','nco2015_code','isco08_major_group'):
        if row.get(key) is not None:
            return { 'field':key, 'original_code':str(row[key]),
                     'precision':row.get('precision','source_classification_requires_review') }
    return None


def build_report(wage_db=None, insights_db=None, snapshot_dir=ROOT/'data', start_year=2015, end_year=2025, acquisition_report=None):
    if not 1960 <= start_year <= end_year <= 2100:
        raise ValueError('Invalid coverage horizon')
    acquisition=json.loads(Path(acquisition_report).read_text()) if acquisition_report else {}
    upstream_missing={}
    for run in acquisition.get('runs',[]):
        for country,periods in (run.get('result') or {}).get('missing_periods_by_country',{}).items():
            upstream_missing[(country,run['provider'],run['dataset'])]=[p['period'] if isinstance(p,dict) else p for p in periods]
    quarantined={}
    for row in acquisition.get('quarantined_observations',[]):
        quarantined.setdefault((row['country'],row['provider'],row['indicator']),set()).add(row['period'])
    files, snap_rows = snapshots(snapshot_dir)
    stored, economic, failures = database_rows(wage_db)
    extra, econ2, fail2 = database_rows(insights_db)
    stored.extend(extra)
    for key, values in econ2.items():
        economic.setdefault(key,set()).update(values)
    failures.extend(fail2)
    countries = []
    mappings = []
    for country in COUNTRY_MAP:
        observed = [r for r in stored if r.get('country') == country]
        supplied = [r for r in snap_rows if r.get('country') == country]
        occupations = []
        for job in OCCUPATIONS:
            occupation = job['id']
            dbrows = [r for r in observed if r.get('occupation') == occupation]
            sr = [r for r in supplied if r.get('occupation') == occupation]
            originals = sorted({period(r) for r in dbrows})
            years = {int(p) for p in originals if re.fullmatch(r'\d{4}',p)}
            audit = source_audit(country)
            if dbrows:
                status = 'stored_observations'
            elif sr:
                status = 'snapshot_not_imported'
            elif audit.get('status') == 'official_group_data_only':
                status = 'incompatible_classification_in_audited_source'
            else:
                status = 'no_observation_source_not_yet_verified'
            occupations.append({'occupation':occupation,'status':status,
                'stored_observations':len(dbrows),'snapshot_records':len(sr),
                'original_periods':originals,'snapshot_periods':sorted({period(r) for r in sr}),
                'missing_target_years':[y for y in range(start_year,end_year+1) if y not in years],
                'annual_history_note':'Only exact YYYY periods count as individual years; multi-year periods are not split',
                'stored_geographies':sorted({geography(r) for r in dbrows}),
                'snapshot_geographies':sorted({geography(r) for r in sr}),
                'missing_configured_regions_in_db':[code for code,_ in REGIONS.get(country,{}).get('options',[]) if code not in {geography(r) for r in dbrows}],
                'missing_configured_regions_in_snapshots':[code for code,_ in REGIONS.get(country,{}).get('options',[]) if code not in {geography(r) for r in sr}],
                'regional_status':'stored_regions' if any(geography(r) not in ('national','unknown','None') for r in dbrows) else 'not_observed_region_universe_unverified',
                'source_freshness':'upstream_release_not_checked',
                'definitions':sorted({(str(r.get('measure')),str(r.get('unit')),str(r.get('salary_concept'))) for r in dbrows+sr})})
            seen = set()
            for r in sr:
                c = classification(r)
                if c is None:
                    continue
                marker = json.dumps(c, sort_keys=True)
                if marker in seen:
                    continue
                seen.add(marker)
                mappings.append({'country':country,'occupation':occupation,**c,
                    'source_url':r.get('source_url'),'snapshot':r['file'],
                    'status':'inherited_reviewed_snapshot_mapping_requires_release_validation',
                    'is_universal_one_to_one':False})
        indicators = []
        for name in INDICATORS:
            periods = sorted(economic.get((country,'observations',name),set()))
            indicators.append({'indicator':name,'periods':periods,'observations':len(periods),
                'status':'stored' if periods else 'missing_import_or_upstream_unknown',
                'upstream_missing_periods':sorted(upstream_missing.get((country,'world_bank',name),[])),
                'quarantined_periods':sorted(quarantined.get((country,'world_bank',name),set())),
                'missing_target_years':[y for y in range(start_year,end_year+1) if str(y) not in periods]})
        from app.eurostat_economy import SERIES, EUROSTAT_COUNTRIES
        euro = [{'indicator':name,'periods':sorted(economic.get((country,'eurostat_observations',name),set())),
                 'status':'stored' if economic.get((country,'eurostat_observations',name)) else 'missing_import_or_upstream_unknown',
                 'upstream_missing_periods':sorted(upstream_missing.get((country,'eurostat',name),[])),
                 'quarantined_periods':sorted(quarantined.get((country,'eurostat',name),set()))}
                for name in SERIES] if country in EUROSTAT_COUNTRIES else []
        countries.append({'country':country,'occupations':occupations,'world_bank':indicators,
            'eurostat':euro,'source_audit':source_audit(country),
            'unmapped_or_group_snapshot_records':sum(1 for r in supplied if not r.get('occupation')),
            'source_candidates':[s['id'] for s in catalogue() if country in s['countries']]})
    return {'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'explicit local DBs and committed snapshots; not a production inventory',
        'database_scope':{'wages_supplied':wage_db is not None,'insights_supplied':insights_db is not None},
        'target_years':[start_year,end_year],'country_count':len(countries),
        'occupation_pairs':len(countries)*len(OCCUPATIONS),
        'summary':{'stored_wage_observations':len(stored),'snapshot_records':sum(f['records'] for f in files),'normalized_snapshot_references':len(snap_rows),
            'pairs_with_snapshot':sum(o['snapshot_records']>0 for c in countries for o in c['occupations']),
            'pairs_with_stored_observations':sum(o['stored_observations']>0 for c in countries for o in c['occupations']),
            'stored_economic_observations':sum(len(v) for v in economic.values())},
        'snapshots':files,'countries':countries,'classification_mappings':mappings,
        'failed_updates':failures+[run for run in acquisition.get('runs',[]) if run['status']=='failed'],'source_discovery':catalogue(),
        'acquisition_summary':{k:acquisition.get(k) for k in ('accepted_observations','by_source','quarantined_versions')},
        'reviewed_classification_registry':classification_catalogue(),
        'limitations':['No source absence inferred from empty databases.',
            'Regional identifiers/universe require provider metadata; no cities or regional wages invented.',
            'Existing national source mappings may be narrower or grouped; preserved without asserting universal equivalence.',
            'Latest source releases and stale status require successful upstream metadata checks.',
            'Group rows and third-party derivatives never count as exact official new wages.']}


def markdown(report):
    lines = ['# Inventário de aquisição em massa', '', report['scope'], '',
        '| País | Pares com observações locais | Pares com snapshot | Registos de grupos no snapshot |',
        '| --- | ---: | ---: | ---: |']
    for c in report['countries']:
        lines.append(f"| {c['country']} | {sum(o['stored_observations']>0 for o in c['occupations'])} | {sum(o['snapshot_records']>0 for o in c['occupations'])} | {c['unmapped_or_group_snapshot_records']} |")
    lines.extend(['','## Limitações','',*('- '+v for v in report['limitations']),
                  '', 'O JSON associado contém cada profissão, períodos, lacunas, fontes e códigos originais.'])
    return '\n'.join(lines)+'\n'


def html_report(report):
    """Standalone offline dashboard. Escape all report data; no remote resources."""
    from html import escape
    rows=[]
    for country in report['countries']:
        for item in country['occupations']:
            cells=[country['country'],item['occupation'],item['status'],
                   str(item['stored_observations']),str(item['snapshot_records']),
                   ', '.join(item['original_periods'] or item['snapshot_periods']) or '—',
                   ', '.join(map(str,item['missing_target_years'])),
                   ', '.join(item['missing_configured_regions_in_db']) or 'universo não verificado / sem lacunas configuradas']
            rows.append('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in cells)+'</tr>')
    summary=report['summary']
    acquisition=report.get('acquisition_summary',{})
    economic='<h2>Indicadores económicos e histórico</h2>'
    economic+='<p>'+str(summary['stored_economic_observations'])+' observações locais · '+str(acquisition.get('quarantined_versions') or 0)+' versões em quarentena · '+str(len(report['failed_updates']))+' atualizações falhadas.</p>'
    if acquisition.get('by_source'):
        economic+='<p>'+escape(' · '.join(source+': '+str(count) for source,count in acquisition['by_source'].items()))+'</p>'
    for country in report['countries']:
        economic+='<details><summary>'+escape(country['country'])+' — indicadores por fonte</summary><ul>'
        for source,items in (('Banco Mundial',country['world_bank']),('Eurostat',country['eurostat'])):
            for item in items:
                periods=item['periods']
                history=(periods[0]+' a '+periods[-1]) if periods else 'sem observações locais'
                missing=len(item.get('upstream_missing_periods',[]))
                quarantine=len(item.get('quarantined_periods',[]))
                label=source+' / '+item['indicator']+': '+str(len(periods))+' observações; '+history+'; '+str(missing)+' períodos ausentes na fonte; '+str(quarantine)+' em quarentena'
                economic+='<li>'+escape(label)+'</li>'
        economic+='</ul></details>'
    economic+='<details><summary>Datasets e fontes descobertos — validação pendente ou concluída</summary><ul>'
    for source in report['source_discovery']:
        economic+='<li>'+escape(source['id']+' — '+source['status'])+'</li>'
    economic+='</ul></details>'
    return '''<!doctype html><html lang="pt-PT"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EarnWage — cobertura de dados</title>
<style>body{font:16px system-ui;margin:2rem;color:#15243b;background:#f7f9fc}h1{margin-bottom:.3rem}input{padding:.7rem;width:min(90%,36rem)}table{border-collapse:collapse;width:100%;background:white;margin-top:1rem}th,td{padding:.6rem;border:1px solid #dde3ec;text-align:left;font-size:.85rem}th{background:#15243b;color:white}td{max-width:25rem;overflow-wrap:anywhere}.scroll{overflow:auto}small{color:#506075}</style>
<h1>EarnWage — cobertura de dados</h1>
<p>14 países · 40 profissões · 560 pares. Inventário local; não representa a base de produção.</p>
<p>''' + escape(str(summary['pairs_with_stored_observations'])) + ' pares com observações importadas · ' + escape(str(summary['pairs_with_snapshot'])) + ''' pares com registos em snapshots.</p>''' + economic + '''
<h2>Cobertura profissional</h2><label for="filter">Filtrar país, profissão, estado ou período</label><br>
<input id="filter" type="search" placeholder="Ex.: PT, nurse, snapshot_not_imported">
<p id="count" aria-live="polite">560 pares</p><div class="scroll"><table id="coverage">
<thead><tr><th>País</th><th>Profissão</th><th>Estado</th><th>Registos locais</th><th>Registos snapshot</th><th>Períodos originais</th><th>Anos sem observação anual individual</th><th>Regiões configuradas sem registo local</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div>
<p><small>Grupos profissionais não preenchem profissões individuais. Lacunas não provam ausência na fonte. Intervalos plurianuais são preservados. Snapshot disponível não significa importação concluída.</small></p>
<p><a href="inventory.json">Inventário completo JSON</a> · <a href="inventory.md">Relatório em texto</a></p>
<script>const input=document.getElementById('filter');const rows=[...document.querySelectorAll('#coverage tbody tr')];input.addEventListener('input',()=>{const q=input.value.toLowerCase();let count=0;for(const row of rows){row.hidden=!row.textContent.toLowerCase().includes(q);if(!row.hidden)count++;}document.getElementById('count').textContent=count+' pares';});</script></html>'''

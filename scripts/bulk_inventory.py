"""Read-only inventory of explicitly selected local databases and snapshots."""
import argparse
import json
from pathlib import Path
from app.bulk_coverage import build_report, markdown, html_report, ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wage-db',type=Path)
    p.add_argument('--insights-db',type=Path)
    p.add_argument('--snapshot-dir',type=Path,default=ROOT/'data')
    p.add_argument('--start-year',type=int,default=2015)
    p.add_argument('--end-year',type=int,default=2025)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--acquisition-report',type=Path)
    p.add_argument('--staging',type=Path,action='append',default=[])
    p.add_argument('--publication-review',type=Path,help='Explicit offline Phase 4C aggregate review')
    p.add_argument('--production-inventory',type=Path)
    p.add_argument('--inventory-authorization')
    a=p.parse_args()
    report=build_report(a.wage_db,a.insights_db,a.snapshot_dir,a.start_year,a.end_year,a.acquisition_report)
    if a.production_inventory and not a.staging:raise ValueError('Staging required for observation comparison')
    if a.staging:
        from app.bulk_salary_coverage import summarize,attach
        attach(report,summarize(a.staging,a.snapshot_dir,a.production_inventory,a.inventory_authorization))
    if a.publication_review:
        path=a.publication_review
        if path.is_symlink() or not path.is_file() or path.stat().st_size>1_000_000:raise ValueError('Unsafe publication review')
        review=json.loads(path.read_text())
        if review.get('schema')!='earnwage-phase4c-review-v1':raise ValueError('Unknown publication review schema')
        report['publication_review']=review
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (a.output/'inventory.md').write_text(markdown(report))
    (a.output/'dashboard.html').write_text(html_report(report))
    print(json.dumps(report['summary']))

if __name__=='__main__':
    main()

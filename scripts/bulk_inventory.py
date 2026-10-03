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
    a=p.parse_args()
    report=build_report(a.wage_db,a.insights_db,a.snapshot_dir,a.start_year,a.end_year,a.acquisition_report)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (a.output/'inventory.md').write_text(markdown(report))
    (a.output/'dashboard.html').write_text(html_report(report))
    print(json.dumps(report['summary']))

if __name__=='__main__':
    main()

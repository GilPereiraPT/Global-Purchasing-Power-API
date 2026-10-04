"""Reproduce CBS history in explicitly isolated staging; no network/publication."""
import argparse
import json
from pathlib import Path
from scripts.bulk_acquire import safe_workspace, exclusive_worker
from app.bulk_core import BulkStore
from app.nl_cbs_wages import build_history_review, stage_history_review


def execute(source_directory, workspace, acquired_at):
    repository = Path(__file__).resolve().parent.parent
    candidate = Path(workspace).resolve()
    if candidate == repository or repository in candidate.parents:
        raise ValueError('Keep history reviews and staging outside the Git repository')
    root = safe_workspace(workspace)
    for name in ('cbs-history-review.json', 'cbs-history-result.json'):
        if (root/name).is_symlink() or (root/(name + '.tmp')).exists() or (root/(name + '.tmp')).is_symlink():
            raise ValueError('Unsafe CBS review output')
    with exclusive_worker(root):
        review = build_history_review(source_directory, acquired_at)
        store = BulkStore(root/'staging.sqlite3')
        try:
            result = stage_history_review(store, review)
            summary = {**result, 'staging': store.report(),
                       'scope': 'isolated staging only; no production writes'}
            # Atomic output; failed runs cannot leave a truncated success report.
            for name, obj in (('cbs-history-review.json', review),
                              ('cbs-history-result.json', summary)):
                temporary = root/(name + '.tmp')
                created = False
                try:
                    with temporary.open('x', encoding='utf-8') as stream:
                        created = True
                        json.dump(obj, stream, ensure_ascii=False, indent=2)
                        stream.write('\n')
                    temporary.replace(root/name)
                finally:
                    if created:
                        temporary.unlink(missing_ok=True)
            return result
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--acquired-at', required=True, help='Original acquisition timestamp with timezone')
    args = parser.parse_args()
    print(json.dumps(execute(args.source_directory, args.workspace, args.acquired_at)))


if __name__ == '__main__':
    main()

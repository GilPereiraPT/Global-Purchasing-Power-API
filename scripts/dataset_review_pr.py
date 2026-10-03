"""Create a data-only review branch from current main; never update main refs.

Called only by explicitly dispatched original-repository workflows on main.
No feature-branch history is copied, no production HTTP/SSH operation exists.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPOSITORY = 'GilPereiraPT/Global-Purchasing-Power-API'
ALLOWED = frozenset({
    'data/salaries_snapshot.json', 'data/ilostat_group_salaries.json',
    'data/ch_bfs_wages.json', 'data/in_plfs_2025_nco.json',
    'data/north_america_wages.json', 'data/ca_statcan_groups.json',
    'data/ca_province_wages.json', 'data/us_oews_curated.json',
    'data/br_rais_2025_states.json',
})
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 10 * 1024 * 1024


def authorized(env):
    return (env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and env.get('GITHUB_REPOSITORY') == REPOSITORY
            and env.get('GITHUB_REF') == 'refs/heads/main'
            and re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')) is not None
            and re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ID', '')) is not None
            and re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ATTEMPT', '')) is not None)


def api(endpoint, payload=None):
    args = ['gh', 'api', 'repos/' + REPOSITORY + '/' + endpoint]
    if payload is not None:
        args += ['--method', 'POST', '--input', '-']
    result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        # Never print stderr: may contain authenticated URLs or transport headers.
        raise RuntimeError('GitHub dataset review request failed')
    return json.loads(result.stdout)


def publish(paths, env=None):
    env = os.environ if env is None else env
    if not authorized(env):
        raise ValueError('Explicit original-repository main dispatch required')
    if not paths or len(paths) != len(set(paths)) or set(paths) - ALLOWED:
        raise ValueError('Unapproved dataset paths')
    content = {}
    for name in paths:
        path = Path(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ValueError('Unsafe or oversized dataset')
        raw = path.read_bytes()
        json.loads(raw)
        content[name] = raw
    if sum(map(len, content.values())) > MAX_TOTAL:
        raise ValueError('Dataset review exceeds size budget')
    main = api('commits/main')
    if main['sha'] != env['GITHUB_SHA']:
        raise ValueError('Main advanced; dispatch again before publishing')
    tree_sha = main['commit']['tree']['sha']
    existing = {item['path']: item['sha'] for item in api('git/trees/' + tree_sha + '?recursive=1')['tree']}
    changes = []
    for name, raw in content.items():
        digest = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if existing.get(name) == digest:
            continue
        blob = api('git/blobs', {'encoding': 'base64', 'content': base64.b64encode(raw).decode()})
        changes.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    if not changes:
        return {'status': 'unchanged'}
    tree = api('git/trees', {'base_tree': tree_sha, 'tree': changes})
    commit = api('git/commits', {'message': 'data: propose validated dataset update',
                              'tree': tree['sha'], 'parents': [main['sha']]})
    branch = 'data-review/' + env['GITHUB_RUN_ID'] + '-' + env['GITHUB_RUN_ATTEMPT']
    api('git/refs', {'ref': 'refs/heads/' + branch, 'sha': commit['sha']})
    pr = api('pulls', {'base': 'main', 'head': branch,
                       'title': 'data: review validated dataset update',
                       'body': 'Manual acquisition; data-only changes based on exact main commit '
                               + main['sha'] + '. Review source validation before merging. No production import or deployment was requested.'})
    return {'status': 'review_required', 'pull_request': pr['html_url']}


if __name__ == '__main__':
    print(json.dumps(publish(sys.argv[1:])))

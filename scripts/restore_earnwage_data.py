"""Validate and restore data backups into a NEW private directory, never live DBs.

Stop the application before an operator switches DB paths to the recovered files.
This command does not change environment variables or restore runtime code.
"""
import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from scripts.backup_earnwage_data import digest


def restore(backup, output):
    backup, output = Path(backup).resolve(), Path(output).resolve()
    if 'public_html' in output.parts or output.exists():
        raise ValueError('Choose a new private recovery directory')
    manifest = json.loads((backup / 'manifest.json').read_text())
    files = []
    for label in ('insights', 'wages_cache'):
        record = manifest['databases'][label]
        name = label + '.sqlite3'
        if record['file'] != name:
            raise ValueError('Unexpected database file')
        source = backup / name
        if source.is_symlink() or digest(source) != record['sha256']:
            raise ValueError('Backup checksum mismatch')
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup integrity check failed')
        files.append((source, name))
    for name, record in manifest['snapshots'].items():
        if record['status'] != 'backed_up':
            continue
        if Path(name).name != name or not name.endswith('.json'):
            raise ValueError('Unexpected snapshot file')
        source = backup / name
        if source.is_symlink() or digest(source) != record['sha256']:
            raise ValueError('Snapshot checksum mismatch')
        json.loads(source.read_text())
        files.append((source, name))
    output.mkdir(parents=True, mode=0o700)
    try:
        for source, name in files:
            shutil.copyfile(source, output / name)
            (output / name).chmod(0o600)
    except Exception:
        shutil.rmtree(output)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    restore(args.backup, args.output)
    print('Recovery copy validated. Live databases and configuration unchanged.')


if __name__ == '__main__':
    main()

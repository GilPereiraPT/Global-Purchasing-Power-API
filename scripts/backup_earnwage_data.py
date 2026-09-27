"""Consistent, non-destructive backup before consolidating production imports.

Run from EarnWage application root:
  python -m scripts.backup_earnwage_data --output /ABSOLUTE/PRIVATE/earnwage-backup-YYYYMMDD

Explicit, persistent EARNWAGE_INSIGHTS_DB and GPP_CACHE_DB are required.
Never place output under public_html. SQLite online backup preserves WAL data.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
ENV_DATABASES = (("insights", "EARNWAGE_INSIGHTS_DB"),
                 ("wages_cache", "GPP_CACHE_DB"))
SNAPSHOTS = ("salaries_snapshot.json", "north_america_wages.json",
             "ilostat_group_salaries.json")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(output):
    destination = Path(output).expanduser()
    if not destination.is_absolute():
        raise ValueError("Choose an absolute private backup path")
    destination = destination.resolve()
    if "public_html" in destination.parts:
        raise ValueError("Never back up database under public_html")
    if destination.exists():
        raise FileExistsError("Backup destination already exists: " + str(destination))

    sources = []
    for label, env in ENV_DATABASES:
        raw = os.getenv(env)
        if not raw:
            raise ValueError(env + " must point to the existing persistent SQLite DB")
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError("Configured database is missing: " + env)
        if path == destination or destination in path.parents:
            raise ValueError("Backup path must not contain a source database")
        sources.append((label, path))
    if sources[0][1] == sources[1][1]:
        raise ValueError("Separate insights and wages/cache databases expected")

    destination.mkdir(parents=True)
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(),
                "databases": {}, "snapshots": {}}
    for label, path in sources:
        target = destination / (label + ".sqlite3")
        connection = sqlite3.connect(
            "file:" + quote(str(path), safe="/") + "?mode=ro", uri=True)
        try:
            backup_db = sqlite3.connect(str(target))
            try:
                connection.backup(backup_db)
                check = backup_db.execute("PRAGMA integrity_check").fetchone()[0]
                if check != "ok":
                    raise ValueError("SQLite integrity check failed: " + label)
            finally:
                backup_db.close()
        finally:
            connection.close()
        manifest["databases"][label] = {
            "file": target.name, "bytes": target.stat().st_size,
            "sha256": digest(target), "integrity": "ok",
        }
    for name in SNAPSHOTS:
        source = ROOT / "data" / name
        if not source.is_file():
            manifest["snapshots"][name] = {"status": "not_present"}
            continue
        target = destination / name
        shutil.copy2(source, target)
        manifest["snapshots"][name] = {
            "status": "backed_up", "bytes": target.stat().st_size,
            "sha256": digest(target),
        }
    manifest_file = destination / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    print("Backup complete:", str(destination), flush=True)
    print(json.dumps(manifest, indent=2), flush=True)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True,
                        help="New absolute directory outside public_html")
    args = parser.parse_args(argv)
    backup(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

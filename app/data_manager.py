"""EarnWage Data Manager: authenticated, bounded, browser/GitHub-driven imports.

Every operation is one HTTP request. Never offer an unauthenticated importer or
allow arbitrary source URLs, SQL, filesystem paths, batches or commands.
"""
import ast
import fcntl
import hmac
import io
import json
import logging
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import httpx

from app.country_insights import INDICATORS, ISO3, _fetch
from app.country_insights_store import connect as economic_connect, read_indicator, save_result
from app.eurostat_economy import (
    EUROSTAT_COUNTRIES, SERIES, ensure_tables, fetch as fetch_eurostat,
    read as read_eurostat, save as save_eurostat,
)

LOG = logging.getLogger("earnwage.data_manager")
ROOT = Path(__file__).resolve().parent.parent
ALLOW_ORIGIN = "https://gilpereirapt.github.io"
MANAGER_VERSION = "0.3.0"
BACKUP_DIR = ROOT / "_earnwage_backups"

ALLOWED_ACTIONS = ("backup", "import", "status", "deploy")
ALLOWED_SOURCES = ("world_bank", "eurostat")
GITHUB_REPOSITORY = "GilPereiraPT/Global-Purchasing-Power-API"
GITHUB_API = "https://api.github.com/repos/" + GITHUB_REPOSITORY
MAX_DEPLOY_ARCHIVE_BYTES = 20 * 1024 * 1024
DEPLOY_REQUIRED = {
    "app/native_wsgi.py", "app/data_manager.py",
    "passenger_wsgi.py", "requirements.txt",
    "scripts/backup_earnwage_data.py", "scripts/restore_earnwage_data.py",
    "scripts/deploy_runtime.py",
}


def _response(reply, start_response, origin, code, body):
    return reply(start_response, body, code, "POST", origin)


def _authorize(environ):
    secret = os.environ.get("EARNWAGE_ADMIN_TOKEN", "")
    if len(secret) < 32:
        return "admin_not_configured"
    supplied = environ.get("HTTP_X_EARNWAGE_ADMIN_TOKEN", "")
    if not supplied or not hmac.compare_digest(secret, supplied):
        return "unauthorized"
    if environ.get("HTTP_ORIGIN") not in (None, ALLOW_ORIGIN):
        return "forbidden_origin"
    return None


def _parse(environ):
    size = int(environ.get("CONTENT_LENGTH", "0") or "0")
    if not 0 < size <= 1024:
        raise ValueError("Invalid JSON request length")
    payload = json.loads(environ["wsgi.input"].read(size).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


@contextmanager
def _exclusive_operation():
    # Same lock for every Passenger worker and the optional offline cron
    # operations which use this same function. No user-supplied path.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    file_path = BACKUP_DIR / ".data-manager.lock"
    with file_path.open("a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another_import_is_running")
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _audit_db(db):
    db.execute("""CREATE TABLE IF NOT EXISTS data_manager_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempted_at TEXT NOT NULL,
        source TEXT NOT NULL,
        country TEXT NOT NULL,
        indicator TEXT NOT NULL,
        mode TEXT NOT NULL,
        status TEXT NOT NULL,
        observations INTEGER NOT NULL,
        error_type TEXT
    )""")


def _record(db, source, country, indicator, mode, status, count, error=None):
    _audit_db(db)
    db.execute("""INSERT INTO data_manager_activity
        (attempted_at,source,country,indicator,mode,status,observations,error_type)
        VALUES (?,?,?,?,?,?,?,?)""", (
            datetime.now(timezone.utc).isoformat(), source, country, indicator,
            mode, status, count, error))
    db.commit()


def _backup_readiness():
    """Return safe diagnostic labels, not private filesystem paths or secrets."""
    from app.store import DB_PATH as active_cache_db
    # Never call db_path() before checking for relative configuration: it
    # deliberately raises ValueError and would incorrectly return HTTP 422.
    expected = {
        "EARNWAGE_INSIGHTS_DB": Path(
            os.environ.get("EARNWAGE_INSIGHTS_DB")
            or "/tmp/earnwage_country_insights.sqlite3"),
        "GPP_CACHE_DB": Path(active_cache_db),
    }
    sources = {}
    for variable, active_path in expected.items():
        configured = os.environ.get(variable, "")
        if not configured:
            state = "variable_missing"
        else:
            path = Path(configured).expanduser()
            if not path.is_absolute():
                state = "path_not_absolute"
            elif path.resolve() != active_path.expanduser().resolve():
                state = "path_differs_from_active_database"
            elif not path.is_file():
                state = "configured_database_missing"
            else:
                state = "ready"
        sources[variable] = state
    root = BACKUP_DIR.resolve()
    if "public_html" in root.parts:
        destination = "unsafe_public_directory"
    elif not BACKUP_DIR.exists() and not BACKUP_DIR.parent.is_dir():
        destination = "parent_missing"
    else:
        destination = "ready_for_attempt"
    return {
        "ready": all(v == "ready" for v in sources.values())
                 and destination == "ready_for_attempt",
        "databases": sources,
        "destination": destination,
        "note": "No database paths or private credentials are returned.",
    }


def _backups():
    if not BACKUP_DIR.is_dir():
        return []
    # Never disclose the actual server filesystem path in API responses.
    return [p.name for p in sorted(BACKUP_DIR.iterdir(), reverse=True)
            if p.is_dir() and p.name.startswith("backup-") and
            (p / "manifest.json").is_file()][:20]


def _backup(payload):
    if payload:
        raise ValueError("Backup does not accept user parameters")
    readiness = _backup_readiness()
    if not readiness["ready"]:
        return {"status": "prerequisites_missing",
                "backup_readiness": readiness,
                "note": "Check the indicated variables in cPanel Setup Python App. Do not create new empty databases."}
    from scripts.backup_earnwage_data import backup
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = BACKUP_DIR / ("backup-" + stamp)
    # Disallow backup creation inside publicly served directory.
    if "public_html" in destination.resolve().parts:
        raise ValueError("Unsafe backup location")
    manifest = backup(str(destination))
    return {
        "status": "available",
        "backup_id": destination.name,
        "databases": {
            label: {"integrity": data["integrity"], "bytes": data["bytes"]}
            for label, data in manifest["databases"].items()
        },
        "snapshots": {
            label: data["status"]
            for label, data in manifest["snapshots"].items()
        },
        "note": "Private SQLite online backup completed; no data was imported.",
    }


def _status(payload):
    if payload:
        raise ValueError("Status does not accept user parameters")
    with economic_connect() as db:
        _audit_db(db)
        rows = db.execute("""SELECT attempted_at,source,country,indicator,
           mode,status,observations,error_type FROM data_manager_activity
           ORDER BY id DESC LIMIT 60""").fetchall()
    columns = ("attempted_at", "source", "country", "indicator",
               "mode", "status", "observations", "error_type")
    return {"status": "ok", "history": [
        dict(zip(columns, row)) for row in rows],
        "backups": _backups(), "backup_readiness": _backup_readiness(),
        "manager_version": MANAGER_VERSION,
        "indicators": list(INDICATORS),
        "world_bank_countries": list(ISO3),
        "eurostat_countries": list(EUROSTAT_COUNTRIES),
        "eurostat_indicators": list(SERIES),
        "note": "Activity logs are recorded when imports run via this Data Manager.",
    }


def _import_one(payload):
    if set(payload) - {"source", "country", "indicator", "mode", "dry_run"}:
        raise ValueError("Unsupported import parameters")
    source, country = payload.get("source"), payload.get("country")
    indicator, mode = payload.get("indicator"), payload.get("mode", "missing")
    dry_run = payload.get("dry_run", False)
    if source not in ALLOWED_SOURCES or mode not in ("missing", "refresh") \
            or not isinstance(dry_run, bool):
        raise ValueError("Unsupported source or mode")
    if source == "world_bank":
        if country not in ISO3 or indicator not in INDICATORS:
            raise ValueError("Unsupported World Bank selection")
    else:
        if country not in EUROSTAT_COUNTRIES or indicator not in SERIES:
            raise ValueError("Unsupported Eurostat/ONS/OECD selection")

    with economic_connect() as db:
        if source == "world_bank":
            prior = read_indicator(db, country, indicator)
        else:
            ensure_tables(db)
            prior = read_eurostat(db, country, indicator)
        if mode == "missing" and prior["status"] == "available":
            return {"import_status": "skipped_existing", "previous": prior,
                    "source": source, "country": country,
                    "indicator": indicator, "dry_run": dry_run}
        if dry_run:
            return {"import_status": "would_import", "previous": prior,
                    "source": source, "country": country,
                    "indicator": indicator, "dry_run": True}

    if not _backups():
        return {
            "import_status": "backup_required",
            "source": source, "country": country, "indicator": indicator,
            "note": "Create a private online backup before any first import.",
        }

    # External request OUTSIDE SQLite transaction: do not hold a database
    # writer lock while waiting for World Bank, Eurostat or ONS.
    if source == "world_bank":
        # Force source re-attempts (including recent prior failures). The
        # short-lived in-process _fetch cache must not mask explicit refresh.
        from app import country_insights
        with country_insights._LOCK:
            country_insights._CACHE.pop((country, INDICATORS[indicator][0]), None)
        status, observations, error = _fetch(country, INDICATORS[indicator][0])
        outcome = ("available" if observations else "empty") if status == "available" \
            else "failed"
    else:
        try:
            observations = fetch_eurostat(country, SERIES[indicator])
            status = "available" if observations else "empty"
            error = None
        except Exception as exc:
            from urllib.error import HTTPError, URLError
            if not isinstance(exc, (HTTPError, URLError, TimeoutError, ValueError,
                                    KeyError, TypeError, OSError)):
                LOG.exception("Unexpected economic source failure")
            observations, status, error = [], "failed", type(exc).__name__
        outcome = status

    with economic_connect() as db:
        if source == "world_bank":
            save_result(db, country, indicator, observations, status, error)
            after = read_indicator(db, country, indicator)
        else:
            ensure_tables(db)
            save_eurostat(db, country, indicator, observations, status, error)
            after = read_eurostat(db, country, indicator)
        _record(db, source, country, indicator, mode, outcome,
                len(observations), error)
    return {
        "import_status": outcome, "observation_count": len(observations),
        "source": source, "country": country, "indicator": indicator,
        "data": after, "dry_run": False,
    }



def _deploy_allowed(path):
    """Closed runtime allow-list; never deploy server-private or executable extras."""
    item = PurePosixPath(path)
    if ".." in item.parts or path.startswith("/") or any(part.startswith(".") for part in item.parts):
        return False
    if len(item.parts) == 2 and item.parts[0] == "app" and item.suffix == ".py":
        return True
    if len(item.parts) == 2 and item.parts[0] == "data" and item.suffix == ".json":
        return True
    if len(item.parts) == 2 and item.parts[0] == "scripts" and item.suffix == ".py":
        return True
    return path in ("passenger_wsgi.py", "requirements.txt")


def _github_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "EarnWage-Production-Data-Manager",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
    response.raise_for_status()
    if len(response.content) > 2_000_000:
        raise ValueError("Unexpected GitHub metadata size")
    return response.json()


def _tested_main_commit():
    commit = _github_json(GITHUB_API + "/commits/main")
    sha = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid GitHub main commit")
    runs = _github_json(GITHUB_API + "/actions/runs?head_sha=" + sha + "&per_page=20")
    candidates = [
        run for run in runs.get("workflow_runs", [])
        if run.get("name") == "API tests" and run.get("head_sha") == sha
        and run.get("event") == "push"
        and run.get("head_branch") == "main"
        and run.get("head_repository", {}).get("full_name") == GITHUB_REPOSITORY
    ]
    if not any(run.get("status") == "completed" and run.get("conclusion") == "success"
               for run in candidates):
        raise RuntimeError("github_tests_not_green")
    return sha


def _runtime_members(archive):
    members = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        parts = PurePosixPath(info.filename).parts
        if len(parts) < 2:
            continue
        relative = "/".join(parts[1:])
        if not _deploy_allowed(relative):
            continue
        if info.file_size > 5_000_000:
            raise ValueError("Unexpected runtime file size")
        members[relative] = info
    missing = sorted(DEPLOY_REQUIRED - set(members))
    if missing:
        raise ValueError("GitHub runtime bundle missing required files")
    return members


def _validate_staged_runtime(staging, paths):
    version = None
    for relative in paths:
        file_path = staging / relative
        if relative.endswith(".py"):
            ast.parse(file_path.read_text(encoding="utf-8"), filename=relative)
        elif relative.startswith("data/") and relative.endswith(".json"):
            json.loads(file_path.read_text(encoding="utf-8"))
    native = (staging / "app" / "native_wsgi.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', native, re.M)
    if not match:
        raise ValueError("VERSION missing from staged native_wsgi.py")
    version = match.group(1)
    return version


def _code_backup(paths):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = BACKUP_DIR / ("code-predeploy-" + stamp + ".tar.gz")
    with tarfile.open(destination, "w:gz") as archive:
        for relative in paths:
            source = ROOT / relative
            if source.is_file():
                archive.add(source, arcname=relative, recursive=False)
    backups = sorted(BACKUP_DIR.glob("code-predeploy-*.tar.gz"), reverse=True)
    for old in backups[5:]:
        try:
            old.unlink()
        except OSError:
            LOG.warning("Could not prune old code backup")
    return destination.name


def _deploy(payload):
    if payload != {"confirm": "deploy_tested_main"}:
        raise ValueError("Explicit deploy confirmation required")

    sha = _tested_main_commit()
    archive_url = (
        "https://github.com/" + GITHUB_REPOSITORY + "/archive/" + sha + ".zip"
    )
    response = httpx.get(
        archive_url,
        headers={"User-Agent": "EarnWage-Production-Data-Manager"},
        timeout=45,
        follow_redirects=True,
    )
    response.raise_for_status()
    if not response.content or len(response.content) > MAX_DEPLOY_ARCHIVE_BYTES:
        raise ValueError("Unexpected GitHub deployment archive size")

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        members = _runtime_members(archive)
        with tempfile.TemporaryDirectory(prefix=".earnwage-stage-", dir=ROOT) as temp:
            staging = Path(temp)
            for relative, info in members.items():
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            version = _validate_staged_runtime(staging, members)

            backup_id = _code_backup(members)
            for relative in sorted(members):
                source = staging / relative
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".deploy-tmp")
                shutil.copy2(source, temporary)
                os.replace(temporary, target)

    restart = ROOT / "tmp" / "restart.txt"
    restart.parent.mkdir(parents=True, exist_ok=True)
    restart.touch()

    return {
        "status": "deployed",
        "commit": sha,
        "version": version,
        "files_updated": len(members),
        "backup_id": backup_id,
        "restart_requested": True,
        "note": (
            "Validated GitHub main deployed from a successful API tests run. "
            "Passenger restart requested; poll /v1/health for the new version."
        ),
    }

def _safe_backup_failure(exc):
    """Classify known backup issues without revealing paths or internals."""
    reason = str(exc)
    if isinstance(exc, PermissionError):
        return "backup_permission_denied"
    if isinstance(exc, FileNotFoundError):
        return "configured_database_missing"
    if "integrity check failed" in reason:
        return "sqlite_integrity_check_failed"
    if "Separate insights and wages/cache databases expected" in reason:
        return "both_database_variables_point_to_same_file"
    if "existing persistent SQLite DB" in reason:
        return "database_variable_missing"
    if "public_html" in reason or "Unsafe backup location" in reason:
        return "unsafe_backup_location"
    if "Backup destination already exists" in reason:
        return "backup_destination_already_exists"
    if isinstance(exc, sqlite3.Error):
        return "sqlite_backup_failed"
    return "backup_preparation_failed"


def handle(environ, start_response, origin, action, reply):
    """Entry from the production WSGI adapter; never return internal tracebacks."""
    auth = _authorize(environ)
    if auth:
        code = 503 if auth == "admin_not_configured" else (
            403 if auth == "forbidden_origin" else 401)
        return _response(reply, start_response, origin, code, {"error": auth})
    if action not in ALLOWED_ACTIONS:
        return _response(reply, start_response, origin, 404,
                         {"error": "unknown_manager_action"})
    try:
        payload = _parse(environ)
        if action == "status":
            result = _status(payload)
        else:
            with _exclusive_operation():
                if action == "backup":
                    result = _backup(payload)
                elif action == "deploy":
                    result = _deploy(payload)
                else:
                    result = _import_one(payload)
        code = (409 if result.get("import_status") == "backup_required"
                or result.get("status") == "prerequisites_missing" else 200)
        return _response(reply, start_response, origin, code, result)
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        if action == "backup":
            LOG.warning("Data Manager backup preparation failed (%s)", type(exc).__name__)
            return _response(reply, start_response, origin, 409, {
                "error": "backup_failed",
                "reason": _safe_backup_failure(exc),
                "backup_readiness": _backup_readiness(),
                "manager_version": MANAGER_VERSION,
            })
        return _response(reply, start_response, origin, 422,
                         {"error": "invalid_manager_request"})
    except RuntimeError as exc:
        if str(exc) == "another_import_is_running":
            return _response(reply, start_response, origin, 409,
                             {"error": "another_import_is_running"})
        if str(exc) == "github_tests_not_green":
            return _response(reply, start_response, origin, 409, {
                "error": "github_tests_not_green",
                "note": "The latest main commit is not deployable until API tests complete successfully.",
                "manager_version": MANAGER_VERSION,
            })
        LOG.exception("Data Manager runtime failure")
    except (sqlite3.Error, OSError) as exc:
        LOG.exception("Data Manager storage or source failure")
        if action == "backup":
            return _response(reply, start_response, origin, 503, {
                "error": "backup_failed",
                "reason": _safe_backup_failure(exc),
                "manager_version": MANAGER_VERSION,
            })
    except Exception:
        LOG.exception("Unexpected Data Manager error")
    return _response(reply, start_response, origin, 503,
                     {"error": "manager_operation_failed",
                      "note": "See Passenger logs; no existing observations were deliberately deleted."})

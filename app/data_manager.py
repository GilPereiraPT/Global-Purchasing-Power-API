"""EarnWage Data Manager: authenticated, bounded, browser/GitHub-driven imports.

Every operation is one HTTP request. Never offer an unauthenticated importer or
allow arbitrary source URLs, SQL, filesystem paths, batches or commands.
"""
import fcntl
import hmac
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.country_insights import INDICATORS, ISO3, _fetch
from app.country_insights_store import connect as economic_connect, read_indicator, save_result
from app.eurostat_economy import (
    EUROSTAT_COUNTRIES, SERIES, ensure_tables, fetch as fetch_eurostat,
    read as read_eurostat, save as save_eurostat,
)

LOG = logging.getLogger("earnwage.data_manager")
ROOT = Path(__file__).resolve().parent.parent
ALLOW_ORIGIN = "https://gilpereirapt.github.io"
BACKUP_DIR = ROOT / "_earnwage_backups"

ALLOWED_ACTIONS = ("backup", "import", "status")
ALLOWED_SOURCES = ("world_bank", "eurostat")


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
        "backups": _backups(), "indicators": list(INDICATORS),
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
                result = _backup(payload) if action == "backup" else _import_one(payload)
        code = 409 if result.get("import_status") == "backup_required" else 200
        return _response(reply, start_response, origin, code, result)
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        return _response(reply, start_response, origin, 422,
                         {"error": "invalid_manager_request"})
    except RuntimeError as exc:
        if str(exc) == "another_import_is_running":
            return _response(reply, start_response, origin, 409,
                             {"error": "another_import_is_running"})
        LOG.exception("Data Manager runtime failure")
    except (sqlite3.Error, OSError):
        LOG.exception("Data Manager storage or source failure")
    except Exception:
        LOG.exception("Unexpected Data Manager error")
    return _response(reply, start_response, origin, 503,
                     {"error": "manager_operation_failed",
                      "note": "See Passenger logs; no existing observations were deliberately deleted."})

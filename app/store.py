"""Small durable HTTP response cache for Passenger and local development."""
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = os.getenv("GPP_CACHE_DB", "/tmp/gpp_api_cache.sqlite3")


def connect():
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS cache "
        "(cache_key TEXT PRIMARY KEY, response TEXT NOT NULL, fetched_at INTEGER NOT NULL)"
    )
    return connection


def get(key, ttl):
    with connect() as db:
        row = db.execute("SELECT response, fetched_at FROM cache WHERE cache_key=?", (key,)).fetchone()
    if not row:
        return None
    # Expired values are not served as current observations.
    if not 0 <= time.time() - row[1] <= ttl:
        return None
    return json.loads(row[0])


def set_value(key, data):
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO cache (cache_key,response,fetched_at) VALUES (?,?,?)",
            (key, json.dumps(data, ensure_ascii=False), int(time.time())),
        )

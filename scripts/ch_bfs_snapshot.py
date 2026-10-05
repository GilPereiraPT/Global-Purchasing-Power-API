"""Acquire the reviewed BFS historical cube, preserving original checksums."""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.ch_bfs_wages import API_URL, decode_snapshot, load_snapshot, reviewed_query

REUSE_URL = "https://www.geo.admin.ch/de/newnsb/f1zWSNpVPekdwKPMGT9dd"


def publish(snapshot):
    """Apply the reviewed federal-statistics reuse basis to this public table."""
    if snapshot.get("table") != "px-x-0304010000_205":
        raise ValueError("Unreviewed table")
    snapshot["licence_status"] = "federal_statistics_free_reuse_with_attribution"
    snapshot["publication_status"] = "public_with_attribution"
    snapshot["reuse"] = {
        "source_url": REUSE_URL,
        "announcement_date": "2026-06-05",
        "effective_date": "2026-07-15",
        "reviewed_at": "2026-10-05",
        "basis": "Published federal statistical results may be reused and redistributed, including commercially, with source attribution.",
        "attribution": "Source: Swiss Federal Statistical Office (FSO), Swiss Earnings Structure Survey (ESS), table px-x-0304010000_205. Processed by EarnWage.",
    }
    return snapshot


def acquire(output, originals):
    originals.mkdir(parents=True, exist_ok=True)
    def request(body=None):
        req = urllib.request.Request(API_URL, data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as response:
            data = response.read(5_000_001)
            if len(data) > 5_000_000:
                raise ValueError("Oversized BFS response")
            return data
    metadata = request()
    query = json.dumps(reviewed_query(json.loads(metadata)), ensure_ascii=False,
                       separators=(",", ":")).encode()
    data = request(query)
    provenance = {"url": API_URL, "status": 200,
                  "acquired_at": datetime.now(timezone.utc).isoformat()}
    for name, body, field in (("metadata.json", metadata, "metadata_sha256"),
                              ("query.json", query, "query_sha256"),
                              ("response.json", data, "sha256")):
        (originals / name).write_bytes(body)
        provenance[field] = hashlib.sha256(body).hexdigest()
    snapshot = publish(decode_snapshot(metadata, data, query, provenance))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    rows = load_snapshot(output)
    if not rows:
        raise ValueError("Empty publication")
    print(json.dumps({"cells": len(rows), "accepted": sum(r["quality_status"] == "accepted" for r in rows),
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/ch_bfs_wages.json"))
    parser.add_argument("--originals", type=Path, required=True)
    args = parser.parse_args()
    acquire(args.output, args.originals)

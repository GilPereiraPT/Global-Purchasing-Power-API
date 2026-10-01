"""Validate and publish HUMAN-REVIEWED 2025 BA state Berufsgattung extracts.

The BA Entgeltatlas REST endpoint requires appropriate access and sometimes
switches automatically to broader occupation groups or geographic areas.
Therefore a raw HTTP response must NOT be converted directly into salary cells
without source-level review of actual aggregation, year and selected state.
"""
import argparse
import json
from pathlib import Path
from app.de_entgeltatlas_states import validate


def import_reviewed(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    if source == output:
        raise ValueError("Reviewed source and published snapshot must be separate")
    obj = json.loads(source.read_text(encoding="utf-8"))
    results = validate(obj)
    if not results:
        raise ValueError("No independently verified 2025 German state observations to publish")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
    return {
        "verified_cells": len(results),
        "professions": len({job for job, _ in results}),
        "states": len({region for _, region in results}),
        "source": "human-reviewed BA Entgeltatlas 2025 exact Berufsgattung records",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-input", required=True)
    parser.add_argument("--output", default="data/de_entgeltatlas_states_2025.json")
    args = parser.parse_args()
    print(json.dumps(import_reviewed(args.reviewed_input, args.output)))

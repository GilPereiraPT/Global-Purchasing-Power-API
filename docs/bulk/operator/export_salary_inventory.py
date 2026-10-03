"""Compatibility CLI for the shared Phase 4E/4F read-only salary exporter.

Run from a full checkout. For an installed runtime use:
  python -m app.salary_inventory_export --wages-db ... --output ... --authorization ...
The preferred operator procedure is the existing Data Manager export button.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.salary_inventory_export import main

if __name__ == '__main__':
    main()

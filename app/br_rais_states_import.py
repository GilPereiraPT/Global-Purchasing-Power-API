"""Curated six-digit CBO / state median remuneration from 99K RAIS 2025 pages.

Input is the SAME public RAIS-derived aggregator already used in br_rais_wages.
No median interpolation, no combining CBO codes, and no national fallback.
Requires requests and beautifulsoup4 in import-only environment.
"""
import argparse
import json
import re
import time
from pathlib import Path

from app.br_rais_wages import OBSERVATIONS, PERIOD, SOURCE_URL, POPULATION
from app.br_cbo import CBO

UF = {
    "AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia",
    "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
    "MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais",
    "PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí",
    "RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul",
    "RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SP":"São Paulo",
    "SE":"Sergipe","TO":"Tocantins",
}
SOURCE_AGGREGATOR = "99K — public aggregation of MTE RAIS 2025"
MIN_LINKS = 20  # conservative publication threshold independent of upstream
PATTERN = re.compile(r"\d[\d.,]*")


def number(s):
    match = PATTERN.search(s.replace("\xa0", ""))
    if not match:
        raise ValueError("Missing published median or link count")
    return int(match.group().replace(".", "").replace(",", ""))


def extract(html, occupation, expected_code, url, expected_national):
    from bs4 import BeautifulSoup
    doc = BeautifulSoup(html, "html.parser")
    text = doc.get_text(" ", strip=True)
    match = re.search(r"Código CBO\s*(\d{6})", text)
    if not match or match.group(1) != expected_code:
        raise ValueError("CBO mismatch for " + occupation)
    heading = next((tag for tag in doc.find_all(["h2", "h3"])
                    if "Por estado" in tag.get_text(" ", strip=True)), None)
    if heading is None:
        raise ValueError("No state section on " + occupation)
    table = heading.find_next("table")
    if table is None:
        raise ValueError("State table missing for " + occupation)
    head = [t.get_text(" ", strip=True).lower() for t in table.find_all("th")]
    if not all(any(word in h for h in head) for word in ("uf", "mediana", "vínculos")):
        raise ValueError("Unexpected state table headings for " + occupation)
    cells = []
    seen = set()
    for row in table.find_all("tr"):
        items = row.find_all(["td"])
        if len(items) != 3:
            continue
        state = items[0].get_text(" ", strip=True).upper()
        if state not in UF:
            raise ValueError("Unexpected state " + state)
        if state in seen:
            raise ValueError("Repeated state")
        seen.add(state)
        pay = number(items[1].get_text(" ", strip=True))
        links = number(items[2].get_text(" ", strip=True))
        if pay <= 0 or pay > 2000000 or links < 0:
            raise ValueError("Invalid median or employment-link count")
        if links < MIN_LINKS:
            continue  # Published by aggregator; apply additional cautious floor.
        cells.append({
            "occupation": occupation, "uf": state, "uf_name": UF[state],
            "cbo_code": expected_code, "value": pay, "links": links,
            "currency": "BRL", "unit": "BRL/month",
            "measure": "median_december_remuneration",
            "reference_period": PERIOD, "population": POPULATION,
            "precision": "occupation_cbo2002_6_digit",
            "source": SOURCE_AGGREGATOR, "source_url": url,
            "official_underlying_source": SOURCE_URL,
        })
    if not cells:
        raise ValueError("No eligible state observations for " + occupation)
    return cells


def collect(output, delay=0.25):
    import requests
    session = requests.Session()
    session.headers.update({"User-Agent": "EarnWage educational wage data integrity audit (+https://github.com/GilPereiraPT/Global-Purchasing-Power-API)"})
    results = []
    errors = {}
    for occupation, (national, _, slug) in sorted(OBSERVATIONS.items()):
        url = "https://99k.com.br/carreiras/" + slug
        try:
            reply = session.get(url, timeout=25)
            reply.raise_for_status()
            record = extract(reply.text, occupation, CBO[occupation]["code"], url, national)
            results.extend(record)
        except (requests.RequestException, ValueError) as exc:
            errors[occupation] = str(exc)
        time.sleep(delay)
    if errors:
        raise ValueError("Import incomplete; no partial publication: " + json.dumps(errors, ensure_ascii=False))
    payload = {
        "schema": 1, "country": "BR", "reference_period": PERIOD,
        "population": POPULATION, "precision": "occupation_cbo2002_6_digit",
        "source": SOURCE_AGGREGATOR, "underlying_official_source": SOURCE_URL,
        "notes": ("State medians from already-published 99K CBO/UF tables. "
                  "No combined-code occupations; only 40-44 hours contracted; "
                  "at least 20 links per published cell; absent state cells remain unavailable."),
        "records": sorted(results, key=lambda r: (r["occupation"], r["uf"])),
    }
    if len(results) < 100:
        raise ValueError("Too few observed CBO/state cells for a genuine release")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"occupation_count": len(set(r["occupation"] for r in results)),
            "states": len(set(r["uf"] for r in results)),
            "cells": len(results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/br_rais_2025_states.json")
    args = parser.parse_args()
    print(json.dumps(collect(args.output)))

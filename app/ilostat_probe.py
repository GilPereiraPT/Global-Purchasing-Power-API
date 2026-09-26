"""Read-only probe for ILOSTAT endpoint migration; never imports or publishes wages.

Run in GitHub Actions to identify which official catalogue/data transport is
actually reachable before changing the production importer.
"""
import json
import sys

import httpx

URLS = {
    "legacy_catalogue": "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator/table_of_contents_en.csv",
    "api_catalogue": "https://rplumber.ilo.org/metadata/toc/indicator/",
    "api_catalogue_en": "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en",
    "api_catalogue_csv": "https://rplumber.ilo.org/metadata/toc/indicator/table_of_contents_en.csv",
    "api_catalogue_rds": "https://rplumber.ilo.org/files/indicator/table_of_contents_en.rds",
    "legacy_dataset": "https://webapps.ilo.org/ilostat-files/WEB_bulk_download/indicator/EAR_EMTA_SEX_OCU_CUR_NB_A.csv.gz",
    "api_dataset_csv": "https://rplumber.ilo.org/files/indicator/EAR_EMTA_SEX_OCU_CUR_NB_A.csv.gz",
    "api_dataset_rds": "https://rplumber.ilo.org/files/indicator/EAR_EMTA_SEX_OCU_CUR_NB_A.rds",
}


def probe(client, label, url):
    result = {"name": label, "url": url}
    try:
        # Streaming avoids downloading a large official dataset in a diagnostic.
        with client.stream("GET", url, headers={"Range": "bytes=0-4095"}) as response:
            result.update(status=response.status_code,
                          content_type=response.headers.get("content-type", ""),
                          content_length=response.headers.get("content-length", ""),
                          final_url=str(response.url))
            if response.status_code in (200, 206):
                sample = b""
                for chunk in response.iter_bytes():
                    sample += chunk[:max(0, 1024 - len(sample))]
                    if len(sample) >= 1024:
                        break
                result["sample_text"] = sample[:300].decode("utf-8", errors="replace")
                result["sample_hex"] = sample[:32].hex()
    except httpx.HTTPError as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    return result


def main():
    with httpx.Client(timeout=25, follow_redirects=True,
                      headers={"User-Agent": "EarnWage-ILOSTAT-compatibility-check/1.0"}) as client:
        results = [probe(client, name, url) for name, url in URLS.items()]
    for item in results:
        print(json.dumps(item, ensure_ascii=False), flush=True)
    with open("ilostat_probe_results.json", "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    if not any(x.get("status") in (200, 206) for x in results):
        print("No candidate official endpoint returned data; do not import.", file=sys.stderr)
        return 1
    print("Diagnostic complete. HTTP 200 alone does NOT validate dataset format or salary observations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Read-only probe of the proposed ILOSTAT bulk CSV service.

Never publish observations based on an unverified URL, indicator or currency.
Print HTTP status, final URL, content type, encoding and first CSV columns.
"""
import csv
import gzip
import io
import json
import urllib.error
import urllib.request

BASE = "https://ilostat.ilo.org/data/bulk/indicator/"
FILES = [
    "table_of_contents.csv",
    "EAR_EMTA_SEX_OCU_NB_A.csv.gz",
    "EAR_EMTA_SEX_OCU_CUR_NB_A.csv.gz",
    "EAR_4MTH_SEX_OCU_CUR_NB_A.csv.gz",
]
MAX_READ = 3 * 1024 * 1024


def probe(name):
    url = BASE + name
    request = urllib.request.Request(
        url, headers={"User-Agent": "EarnWage-ILOSTAT-source-validation/1.0",
                      "Accept": "text/csv,application/gzip,*/*",
                      "Range": "bytes=0-65535"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(MAX_READ + 1)
            result = {"file": name, "status": response.status,
                      "final_url": response.url,
                      "content_type": response.headers.get("Content-Type"),
                      "content_encoding": response.headers.get("Content-Encoding"),
                      "content_range": response.headers.get("Content-Range"),
                      "content_length": response.headers.get("Content-Length"),
                      "received_bytes": len(data),
                      "truncated": len(data) > MAX_READ,
                      "gzip_signature": data.startswith(b"\x1f\x8b")}
            if name.endswith(".csv") and data:
                first = data.decode("utf-8-sig", errors="replace").splitlines()
                result["header"] = next(csv.reader(first[:1]), [])
                result["first_row"] = next(csv.reader(first[1:2]), [])
            # Partial gzip ranges cannot be reliably decompressed; don't attempt it.
            print(json.dumps(result, ensure_ascii=False))
    except urllib.error.HTTPError as error:
        print(json.dumps({"file": name, "status": error.code,
                          "final_url": error.url,
                          "content_type": error.headers.get("Content-Type"),
                          "error": str(error)}, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"file": name, "error_type": type(error).__name__,
                          "error": str(error)}, ensure_ascii=False))


if __name__ == "__main__":
    for filename in FILES:
        probe(filename)

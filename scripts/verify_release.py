"""Fail deployment unless HTTP health identifies the exact tested release."""
import argparse
import json
import re
import time
from urllib.request import Request, urlopen
from urllib.error import URLError


def healthy(payload, commit, version):
    return (isinstance(payload, dict) and payload.get('status') == 'ok'
            and payload.get('commit') == commit and payload.get('version') == version)


def verify(url, commit, version, attempts=10, interval=6):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid expected commit')
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={'Cache-Control': 'no-cache'}), timeout=15) as response:
                if response.status == 200 and healthy(json.load(response), commit, version):
                    return
        except (URLError, OSError, ValueError, TypeError):
            pass
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise RuntimeError('Production health/commit verification failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    verify(args.url, args.commit, args.version)
    print('Application healthy on exact tested commit ' + args.commit)


if __name__ == '__main__':
    main()

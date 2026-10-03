"""Configurable offline check policy; never activates a cron or production job."""
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent/'data/bulk_refresh_policy.json'


def load(path=DEFAULT):
    data=json.loads(Path(path).read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('providers'),dict):
        raise ValueError('Invalid refresh policy')
    for provider,policy in data['providers'].items():
        days=policy.get('check_interval_days')
        if isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=366:
            raise ValueError('Invalid refresh interval')
    return data


def due(store,provider,dataset,policy,now=None):
    # Failed attempts do not reset the last successful check.
    entry=policy['providers'].get(provider)
    if not entry:raise ValueError('No provider refresh policy')
    row=store.db.execute("SELECT finished_at FROM bulk_runs WHERE provider=? AND dataset=? AND status='complete' ORDER BY id DESC LIMIT 1",
                         (provider,dataset)).fetchone()
    if row is None:return True
    current=now or datetime.now(timezone.utc)
    return (current-datetime.fromisoformat(row[0])).total_seconds()>=entry['check_interval_days']*86400

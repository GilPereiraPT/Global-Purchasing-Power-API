"""Read an explicitly authorized, local JSON inventory; never connects to production."""
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from app.bulk_core import KEY_FIELDS, observation_key


def read_inventory(path, *, authorization):
    if not isinstance(authorization,str) or not authorization.strip():
        raise ValueError('Explicit export authorization reference required')
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>100*1024*1024:
        raise ValueError('Expected bounded regular local inventory export')
    with path.open(encoding='utf-8') as stream:
        data=json.load(stream)
    if data.get('schema')!='earnwage-observation-inventory-v1' or data.get('scope') not in ('complete','partial') or not data.get('exported_at'):
        raise ValueError('Observation-level export schema and scope required')
    try:
        datetime.fromisoformat(data['exported_at'])
    except (TypeError,ValueError):
        raise ValueError('Explicit ISO export date required') from None
    records=data.get('observations')
    if not isinstance(records,list):raise ValueError('Missing observations')
    indexed={}
    for row in records:
        if not isinstance(row,dict) or not set(KEY_FIELDS)|{'value'} <= row.keys():
            raise ValueError('Incomplete observation identity')
        if set(row)-set(KEY_FIELDS)-{'value','dimensions'}:
            raise ValueError('Unregistered fields; relevant scope must use dimensions')
        if any((not isinstance(row[k],str) or not row[k]) and not (k in ('classification','currency') and row[k] is None) for k in KEY_FIELDS):
            raise ValueError('Invalid identity')
        key=observation_key(row)
        if key in indexed:raise ValueError('Duplicate export identity')
        indexed[key]=numeric(row['value'])
    return data,indexed


def numeric(value):
    if value is None:return None
    if isinstance(value,bool):raise ValueError('Invalid boolean salary')
    try:result=Decimal(str(value))
    except InvalidOperation:raise ValueError('Invalid salary') from None
    if not result.is_finite():raise ValueError('Non-finite salary')
    return result


def compare(observations, path=None, *, authorization=None):
    if path is None:return {'status':'not_provided','new':None,'revisions':None,'duplicates':None}
    data,index=read_inventory(path,authorization=authorization)
    result={'status':'compared','scope':data['scope'],'exported_at':data['exported_at'],
            'new':0,'revisions':0,'duplicates':0}
    seen=set()
    for row in observations:
        key=observation_key(row)
        if key in seen:raise ValueError('Duplicate staging identity')
        seen.add(key)
        category='new' if key not in index else 'duplicates' if numeric(row['value'])==index[key] else 'revisions'
        result[category]+=1
    return result

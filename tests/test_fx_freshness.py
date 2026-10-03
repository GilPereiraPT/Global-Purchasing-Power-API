import asyncio,json,time
from datetime import datetime,timezone,timedelta
import httpx,pytest
from app import providers,store,data_inventory
from app.fx_policy import valid_quote


def quote(currency='USD',days=0,value=1.12):
 return {'currency':currency,'units_per_eur':value,'source':'ECB','period':(datetime.now(timezone.utc).date()-timedelta(days=days)).isoformat()}


def transport(monkeypatch,body,status=200):
 original=httpx.AsyncClient
 def handler(request):return httpx.Response(status,text=body)
 monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))


def csv(days=0,currency='USD',value='1.12'):
 p=quote(days=days)['period']
 return 'FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\nD,'+currency+',EUR,SP00,A,'+p+','+value+'\n'


@pytest.mark.parametrize('days',[-1,8,200])
def test_old_or_future_quote_is_not_current(days):assert not valid_quote(quote(days=days),'USD')


@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf'),True,'1.12'])
def test_invalid_rates(value):assert not valid_quote(quote(value=value),'USD')


def test_cache_missing_expired_corrupt_and_future_timestamp(monkeypatch,tmp_path):
 monkeypatch.setattr(store,'DB_PATH',str(tmp_path/'cache.sqlite3'));transport(monkeypatch,csv())
 for raw,age in [(None,0),(json.dumps(quote(days=20)),90000),('invalid',0),(json.dumps(quote()),-3600)]:
  with store.connect() as db:
   db.execute('DELETE FROM cache')
   if raw:db.execute('INSERT INTO cache VALUES(?,?,?)',('ecb:exchange:USD',raw,int(time.time())-age))
   db.commit()
  assert asyncio.run(providers.exchange_rate('USD'))['period']==quote()['period']


@pytest.mark.parametrize('case',['old','future','nan','dimension','oversized','error'])
def test_refresh_never_serves_stale_on_failure(monkeypatch,tmp_path,case):
 monkeypatch.setattr(store,'DB_PATH',str(tmp_path/'cache.sqlite3'));store.set_value('ecb:exchange:USD',quote(days=30))
 body=csv(days=30) if case=='old' else csv(days=-1) if case=='future' else csv(value='NaN') if case=='nan' else csv(currency='CAD') if case=='dimension' else 'x'*65537 if case=='oversized' else ''
 transport(monkeypatch,body,503 if case=='error' else 200)
 with pytest.raises(providers.UpstreamUnavailable):asyncio.run(providers.exchange_rate('USD'))
 assert store.get('ecb:exchange:USD',86400)['period']==quote(days=30)['period']


def test_unsupported_pkr_does_not_fetch_or_serve_cached_guess(monkeypatch,tmp_path):
 monkeypatch.setattr(store,'DB_PATH',str(tmp_path/'cache.sqlite3'));store.set_value('ecb:exchange:PKR',quote(currency='PKR'))
 monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:pytest.fail('unsupported currency fetched'))
 assert asyncio.run(providers.exchange_rate('PKR')) is None
 with store.connect() as db:assert data_inventory._rates(db)['PKR']['status']=='unsupported'


def test_inventory_distinguishes_cache_age_and_quote_age(monkeypatch,tmp_path):
 monkeypatch.setattr(store,'DB_PATH',str(tmp_path/'cache.sqlite3'))
 store.set_value('ecb:exchange:USD',quote(days=30));store.set_value('ecb:exchange:GBP',quote(currency='GBP'))
 with store.connect() as db:
  rates=data_inventory._rates(db)
 assert rates['USD']['status']=='invalid_or_stale_observation' and rates['GBP']['status']=='cached'
 assert rates['CAD']['status']=='not_cached'

"""ECB reference dates and cache freshness are separate, explicit checks."""
from datetime import date, datetime, timezone
import math
import re

CACHE_TTL = 86400
MAX_QUOTE_AGE_DAYS = 7  # Covers non-publication weekends/holidays; never extrapolates.
ECB_CURRENCIES = frozenset('AUD BRL CAD CHF CNY CZK DKK GBP HKD HUF IDR ILS INR ISK JPY KRW MXN MYR NOK NZD PHP PLN RON SEK SGD THB TRY USD ZAR'.split())
REFERENCE_URL = 'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html'


def valid_quote(data, currency, today=None):
    today = today or datetime.now(timezone.utc).date()
    try:
        period = data['period']
        if not isinstance(period,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',period):return False
        age = (today-date.fromisoformat(period)).days
        value = data['units_per_eur']
        return (data['currency']==currency and data['source']=='ECB'
                and currency in ECB_CURRENCIES and type(value) in (int,float)
                and math.isfinite(value) and value>0 and 0<=age<=MAX_QUOTE_AGE_DAYS)
    except (KeyError,ValueError,TypeError,OverflowError):return False

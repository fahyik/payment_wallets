import decimal
import requests
from django.conf import settings

from .models import Currencies
from ..exceptions import InternalServerError

FIXER_IO_KEY = settings.FIXER_IO_KEY


def get_rate(origin_currency, target_currency):
    """
    Workaround for fixer API, because unable to choose base currency on free plan
    Base currency is assumed to be EUR, and EUR has to be in Enum Currencies

    sample response:
    {
        "success":true,
        "timestamp":1542551947,
        "base":"EUR",
        "date":"2018-11-18",
        "rates":{
            "USD":1.142054,
            "GBP":0.889455,
            "EUR":1
        }
    }

    return the exchange rate for converting 1 unit of origin currency to target_currency
    """

    currencies = ",".join(cur.name for cur in Currencies)

    url = "http://data.fixer.io/api/latest?access_key={}&symbols={}".format(FIXER_IO_KEY, currencies)

    response = requests.get(url)

    if response.ok and response.json()['success']:

        try:
            rates = response.json()['rates']

            # TODO: refactor this nasty hardcode, or pay for fixer-io
            origin_rate = rates.get(origin_currency)

            # rebase
            for key, val in rates.items():
                rates[key] = val / origin_rate

            return decimal.Decimal(rates[target_currency])

        except Exception as e:
            raise InternalServerError("Unable to obtain FX rate") from e

    else:
        raise InternalServerError("Unable to obtain FX rate")

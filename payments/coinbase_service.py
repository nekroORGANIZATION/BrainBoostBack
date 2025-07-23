from django.conf import settings
import requests

API_KEY = settings.COINBASE_API_KEY

HEADERS = {
    'X-CC-Api-Key': API_KEY,
    'X-CC-Version': '2018-03-22',
    'Content-Type': 'application/json',
}

def create_coinbase_charge(name, description, amount, currency='USD'):
    url = 'https://api.commerce.coinbase.com/charges'
    payload = {
        "name": name,
        "description": description,
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": str(amount),
            "currency": currency
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()
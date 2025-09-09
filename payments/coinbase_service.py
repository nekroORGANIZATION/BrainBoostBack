from django.conf import settings
import requests
import hmac, hashlib, json

API_KEY = settings.COINBASE_API_KEY
WEBHOOK_SECRET = getattr(settings, "COINBASE_WEBHOOK_SECRET", "")

HEADERS = {
    "X-CC-Api-Key": API_KEY,
    "X-CC-Version": "2018-03-22",
    "Content-Type": "application/json",
}

def create_coinbase_charge(name, description, amount, currency="USD"):
    url = "https://api.commerce.coinbase.com/charges"
    payload = {
        "name": name,
        "description": description,
        "pricing_type": "fixed_price",
        "local_price": {"amount": str(amount), "currency": currency},
    }
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return False
    computed = hmac.new(
        key=WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    # Coinbase присылает 'X-CC-Webhook-Signature' — простой сравнение:
    return hmac.compare_digest(computed, signature or "")

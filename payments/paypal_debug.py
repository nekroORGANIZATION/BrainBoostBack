# payments/paypal_debug.py
from django.conf import settings
import requests

def mask(s: str, keep=4):
    if not s:
        return ""
    s = str(s)
    if len(s) <= keep:
        return "*" * len(s)
    return "*" * (len(s) - keep) + s[-keep:]

def get_mode_base():
    mode = getattr(settings, "PAYPAL_MODE", "sandbox")
    base = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    return mode, base

def try_fetch_access_token():
    mode, base = get_mode_base()
    client_id = getattr(settings, "PAYPAL_CLIENT_ID", "")
    client_secret = getattr(settings, "PAYPAL_CLIENT_SECRET", "")

    r = requests.post(
        f"{base}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    ok = r.status_code == 200
    payload = {}
    try:
        payload = r.json()
    except Exception:
        payload = {"text": r.text}

    return {
        "ok": ok,
        "status_code": r.status_code,
        "mode": mode,
        "client_id_tail": mask(client_id),
        "client_secret_tail": mask(client_secret),
        "response": payload,
    }

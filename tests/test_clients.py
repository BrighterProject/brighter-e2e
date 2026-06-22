import hashlib
import hmac
import json

from e2e.clients import stripe_hooks


def test_signed_headers_match_stripe_scheme():
    payload = json.dumps({"id": "evt_1"}).encode()
    headers = stripe_hooks.signed_headers(payload, secret="whsec_test")
    sig = headers["Stripe-Signature"]
    timestamp = sig.split(",")[0].removeprefix("t=")
    v1 = sig.split("v1=")[1]
    expected = hmac.new(
        b"whsec_test", f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    assert v1 == expected

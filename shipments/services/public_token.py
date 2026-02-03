import base64
import hashlib
import hmac
import time
from django.conf import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_public_token(tracking_no: str, *, ttl_seconds: int = 7 * 24 * 3600) -> str:
    """
    Generate token for public tracking.
    Format: v1.<exp>.<sig>
    - exp: unix timestamp expiry (int)
    - sig: base64url(HMAC_SHA256(secret, f"{tracking_no}.{exp}"))
    """
    exp = int(time.time()) + int(ttl_seconds)
    msg = f"{tracking_no}.{exp}".encode("utf-8")
    secret = settings.SECRET_KEY.encode("utf-8")
    sig = hmac.new(secret, msg, hashlib.sha256).digest()
    return f"v1.{exp}.{_b64url(sig)}"


def verify_public_token(tracking_no: str, token: str) -> bool:
    """
    Verify token. Returns True if valid and not expired.
    """
    try:
        v, exp_str, sig = token.split(".", 2)
        if v != "v1":
            return False

        exp = int(exp_str)
        if exp < int(time.time()):
            return False

        msg = f"{tracking_no}.{exp}".encode("utf-8")
        secret = settings.SECRET_KEY.encode("utf-8")
        expected = hmac.new(secret, msg, hashlib.sha256).digest()
        expected_sig = _b64url(expected)

        # constant-time compare
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False

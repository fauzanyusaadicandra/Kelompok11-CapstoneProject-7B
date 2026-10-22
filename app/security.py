"""Hash password (PBKDF2) dan token sesi bertanda tangan HMAC - hanya pustaka standar."""
import base64, hashlib, hmac, os, time
from . import config

COOKIE = "apd_token"


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(username: str) -> str:
    payload = f"{username}|{int(time.time()) + config.TOKEN_TTL}"
    return base64.urlsafe_b64encode(payload.encode()).decode() + "." + _sign(payload)


def read_token(token: str | None) -> str | None:
    """Mengembalikan username jika token valid dan belum kedaluwarsa."""
    if not token:
        return None
    try:
        b64, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(b64.encode()).decode()
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        user, exp = payload.rsplit("|", 1)
        return user if int(exp) >= time.time() else None
    except Exception:
        return None

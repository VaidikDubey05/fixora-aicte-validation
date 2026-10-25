import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.config import settings

# Attempt to use native bcrypt; provide pure-python PBKDF2-SHA256 fallback for environments without binary packages
try:
    import bcrypt

    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

# Attempt to use PyJWT; provide pure-python HMAC-SHA256 JWT fallback if pyjwt is not installed
try:
    import jwt

    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False


def hash_password(password: str) -> str:
    """Hashes a password using bcrypt (or standard PBKDF2 if bcrypt is unavailable)."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    else:
        # PBKDF2 fallback
        salt = base64.b64encode(hashlib.sha256(str(time.time()).encode()).digest()[:16]).decode()
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"pbkdf2_sha256$100000${salt}${base64.b64encode(derived).decode()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored hash."""
    if not plain_password or not hashed_password:
        return False

    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        if HAS_BCRYPT:
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        return False

    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 4:
            iterations = int(parts[1])
            salt = parts[2]
            expected = parts[3]
            derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
            return hmac.compare_digest(base64.b64encode(derived).decode(), expected)

    return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token with 60-minute default expiration.
    Payload includes standard subject, role, and institution_id claims.
    """
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now_utc.timestamp()),
    })

    if HAS_PYJWT:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    else:
        # Standard pure-python HS256 JWT encoding
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _base64url_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT access token, verifying signature and expiration."""
    try:
        if HAS_PYJWT:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        else:
            # Standard pure-python HS256 JWT decoding
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
            actual_sig = _base64url_decode(sig_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            payload_bytes = _base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            # Validate expiration
            if "exp" in payload and time.time() > payload["exp"]:
                return None
            return payload
    except Exception:
        return None

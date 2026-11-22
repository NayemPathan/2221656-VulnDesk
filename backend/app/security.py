"""
Security & Hashing Utilities (backend/app/security.py)
=====================================================================
WHAT THIS FILE DOES:
1. `hash_password` / `verify_password`: Hashes and verifies user passwords using Argon2id
   via `pwdlib` (OWASP-recommended memory-hard hashing algorithm).
2. `hash_token`: Computes a deterministic SHA-256 hex digest for opaque refresh tokens before
   storing them in the `refresh_token` table.
3. `generate_refresh_token`: Creates a cryptographically random opaque refresh token.

WHY WE WROTE IT THIS WAY:
- Passwords use salted Argon2id so brute-force attacks are slow and memory-expensive.
- Refresh tokens are already 256-bit cryptographically random URL-safe strings, so SHA-256
  allows fast indexed database lookups while ensuring a leaked DB dump cannot be used to
  impersonate active sessions.
=====================================================================
"""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hash = PasswordHash.recommended()


def _apply_pepper(password: str) -> str:
    return hmac.new(
        settings.PASSWORD_PEPPER.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_password(password: str) -> str:
    return password_hash.hash(_apply_pepper(password))


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    if password_hash.verify(_apply_pepper(plain_password), hashed_password):
        return True
    # Optional backwards-compatible check for pre-pepper seeded hashes
    return password_hash.verify(plain_password, hashed_password)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

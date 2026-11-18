"""
Security & Hashing Utilities (backend/app/security.py)
=====================================================================
WHAT THIS FILE DOES:
1. `hash_password` / `verify_password`: Hashes and verifies user passwords using Argon2id
   via `pwdlib` (OWASP-recommended memory-hard hashing algorithm).
2. `hash_token`: Computes a deterministic SHA-256 hex digest for opaque refresh tokens before
   storing them in the `refresh_token` table.

WHY WE WROTE IT THIS WAY:
- Passwords use salted Argon2id so brute-force attacks are slow and memory-expensive.
- Refresh tokens are already 256-bit cryptographically random URL-safe strings, so SHA-256
  allows fast indexed database lookups while ensuring a leaked DB dump cannot be used to
  impersonate active sessions.
=====================================================================
"""

import hashlib
import secrets

from pwdlib import PasswordHash

# Argon2id is required by the authentication schema and dependency manifests.
_password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with a unique random salt."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    """Verify a plaintext password against a stored Argon2id hash."""
    if not password_hash:
        return False
    return _password_hasher.verify(plain_password, password_hash)


def generate_refresh_token() -> str:
    """Generate a cryptographically secure 256-bit URL-safe opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest (64 chars) of an opaque refresh token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
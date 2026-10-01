"""Password hashing and high-entropy bearer-token helpers."""
import hashlib
import secrets

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hasher = PasswordHash.recommended()
# Missing accounts still perform a password verification to reduce timing differences.
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    if not 15 <= len(password) <= 128:
        raise ValueError("Password must contain 15 to 128 characters")
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    if len(password) > 128:
        return False
    try:
        valid = password_hasher.verify(password, stored_hash or _dummy_hash)
    except UnknownHashError:
        return False
    return bool(stored_hash) and valid


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # Fast SHA-256 is appropriate for random 256-bit tokens, not human passwords.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

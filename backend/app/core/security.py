"""
Security utilities: password hashing, JWT tokens, and API Key encryption.

Password hashing uses passlib (bcrypt).
JWT uses python-jose (HS256 by default).
API Key encryption uses AES-256-GCM via the `cryptography` library.
"""
import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_jwt_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return create_jwt_token(
        data={"sub": subject, "type": "access"},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    return create_jwt_token(
        data={"sub": subject, "type": "refresh"},
        expires_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
    )


def decode_jwt_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# API Key / Secret encryption (AES-256-GCM via Fernet)
# ---------------------------------------------------------------------------
def _derive_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from VAULT_ENCRYPTION_KEY."""
    raw = settings.VAULT_ENCRYPTION_KEY.encode()
    if len(raw) == 32:
        import base64
        return base64.urlsafe_b64encode(raw)
    # Pad or hash to 32 bytes
    from hashlib import sha256
    return __import__("base64").urlsafe_b64encode(sha256(raw).digest())


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_fernet_key())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """Encrypt an API key / password for database storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt an API key / password from database storage."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()

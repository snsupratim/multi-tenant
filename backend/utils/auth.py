"""
utils/auth.py – JWT creation, verification, and password hashing
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import settings
from backend.models.db_models import User


# -------------------------------------------------------------------
# PASSWORD HASHING
# -------------------------------------------------------------------

# IMPORTANT:
# bcrypt has a 72-byte limit.
# bcrypt_sha256 first SHA256-hashes the password,
# then safely applies bcrypt.

pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto"
)

bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    """
    Hash user password safely.
    """
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify password against stored hash.
    """
    return pwd_context.verify(plain, hashed)


# -------------------------------------------------------------------
# JWT TOKEN CREATION
# -------------------------------------------------------------------

def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()

    payload.update({
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
    })

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user_id: str, username: str) -> str:
    """
    Create short-lived access token.
    """
    return _create_token(
        {
            "sub": user_id,
            "username": username,
            "type": "access",
        },
        timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        ),
    )


def create_refresh_token(user_id: str) -> str:
    """
    Create long-lived refresh token.
    """
    return _create_token(
        {
            "sub": user_id,
            "type": "refresh",
        },
        timedelta(
            days=settings.jwt_refresh_token_expire_days
        ),
    )


# -------------------------------------------------------------------
# TOKEN VERIFICATION
# -------------------------------------------------------------------

def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -------------------------------------------------------------------
# CURRENT USER DEPENDENCY
# -------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:

    payload = decode_token(credentials.credentials)

    # Ensure access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an access token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await User.find_one(
        User.user_id == user_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive",
        )

    return user
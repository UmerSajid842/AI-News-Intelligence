import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
BEARER_SCHEME = HTTPBearer(auto_error=False)


def _secret_key() -> str:
    return os.getenv("AUTHJWT_SECRET_KEY", "local-development-only-change-me")


def create_access_token(subject: str) -> str:
    """Create a short-lived signed access token for a local user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, _secret_key(), algorithm=JWT_ALGORITHM)
    return token.decode("utf-8") if isinstance(token, bytes) else token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(BEARER_SCHEME),
) -> str:
    """Validate the bearer token and return its subject."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(credentials.credentials, _secret_key(), algorithms=[JWT_ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            raise ValueError("Missing token subject")
        return subject
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

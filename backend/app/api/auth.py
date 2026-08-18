import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..security import create_access_token, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


def _configured_credentials() -> tuple[str, str]:
    username = os.getenv("DEMO_USER", "").strip()
    password = os.getenv("DEMO_PASSWORD", "")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo authentication is not configured. Set DEMO_USER and DEMO_PASSWORD.",
        )
    return username, password


@router.post("/login")
def login(request: LoginRequest):
    """Authenticate the configured local demo user and return a JWT."""
    configured_username, configured_password = _configured_credentials()
    if request.username != configured_username or request.password != configured_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(subject=request.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {"username": current_user}

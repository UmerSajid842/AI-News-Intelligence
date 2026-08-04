from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi_jwt_auth import AuthJWT

from ..security import Settings

router = APIRouter()


@AuthJWT.load_config
def get_config():
    return Settings()


class LoginRequest(BaseModel):
    username: str
    password: str


# Demo credentials - in production, replace with a real user store
DEMO_USERS = {
    "admin": "admin123",
    "user": "user123",
}


@router.post("/login")
def login(request: LoginRequest, authorize: AuthJWT = Depends()):
    """Authenticate a user and return a JWT access token."""
    username = request.username
    password = request.password

    if username not in DEMO_USERS or DEMO_USERS[username] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = authorize.create_access_token(subject=username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(authorize: AuthJWT = Depends()):
    """Return the current authenticated user."""
    authorize.jwt_required()
    current_user = authorize.get_jwt_subject()
    return {"username": current_user}

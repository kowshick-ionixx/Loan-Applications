from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from loan_application.config import settings
from loan_application.db import DbSession
from loan_application.exceptions import InvalidCredentialsError
from loan_application.models import User
from loan_application.schemas.auth import RegisterRequest, TokenResponse
from loan_application.schemas.user import UserOut
from loan_application.security import create_access_token
from loan_application.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    summary="Register Customer",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Request body is missing, not valid JSON, or failed validation"
        },
        status.HTTP_409_CONFLICT: {"description": "Username is already registered"},
    },
)
def register(data: RegisterRequest, db: DbSession) -> User:
    """Create a CUSTOMER login from `username` and `password` only. Then log in
    and create the profile with `POST /api/customers`. A `role` in the body is
    ignored. The password is hashed before it is stored."""
    return auth_service.register(db, data)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Log in and receive an access token",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Username or password is missing"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid username or password"},
    },
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenResponse:
    """
    OAuth2 password flow. Send form data (not JSON):
    `username` and `password`. Returns a bearer token.
    """
    user = auth_service.authenticate_user(db, form.username, form.password)
    if user is None:
        raise InvalidCredentialsError()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )

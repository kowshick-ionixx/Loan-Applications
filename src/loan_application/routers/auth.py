from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from loan_application.config import settings
from loan_application.db import DbSession
from loan_application.models import User
from loan_application.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from loan_application.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=RegisterResponse)
def register(data: RegisterRequest, db: DbSession) -> User:
    return auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> TokenResponse:
    token = auth_service.login(db, form.username, form.password)
    return TokenResponse(
        access_token=token, expires_in=settings.access_token_expire_minutes * 60
    )

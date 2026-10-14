from typing import Annotated

import jwt
from fastapi import Depends, Path, Request
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordBearer

from loan_application.db import MAX_ID, DbSession
from loan_application.exceptions import (
    ForbiddenError,
    ProfileRequiredError,
    UnauthorizedError,
)
from loan_application.logging_config import user_id_var
from loan_application.models import User, UserRole
from loan_application.repositories import user_repository
from loan_application.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

PositiveId = Annotated[int, Path(gt=0, le=MAX_ID)]


def user_id_from_token(token: str | None) -> int:
    if not token:
        raise UnauthorizedError("Not authenticated")
    try:
        return int(decode_token(token)["sub"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise UnauthorizedError() from None


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    user = user_repository.get_by_id(db, user_id_from_token(token))
    if user is None or not user.is_active:
        raise UnauthorizedError()
    user_id_var.set(user.id)
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_customer_profile(user: CurrentUser) -> User:
    if user.role == UserRole.CUSTOMER and user.customer_id is None:
        raise ProfileRequiredError()
    return user


ProfileUser = Annotated[User, Depends(require_customer_profile)]


async def require_officer(user: CurrentUser) -> User:
    if user.role != UserRole.OFFICER:
        raise ForbiddenError()
    return user


OfficerUser = Annotated[User, Depends(require_officer)]


def requires_login(request: Request) -> bool:
    route = request.scope.get("route")
    stack = [route.dependant] if isinstance(route, APIRoute) else []
    while stack:
        dependant = stack.pop()
        if dependant.call is get_current_user:
            return True
        stack.extend(dependant.dependencies)
    return False


async def check_token_before_body(request: Request) -> None:
    """FastAPI parses a JSON body before running dependencies, so a malformed
    body would otherwise answer 400 to a caller who has not even logged in."""
    if requires_login(request):
        user_id_from_token(await oauth2_scheme(request))

from typing import Annotated

import jwt
from fastapi import Depends, Path, Request
from fastapi.security import OAuth2PasswordBearer

from loan_application.db import MAX_ID, DbSession
from loan_application.exceptions import ProfileRequiredError, UnauthorizedError
from loan_application.logging_config import user_id_var
from loan_application.models import User, UserRole
from loan_application.repositories import user_repository
from loan_application.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

PositiveId = Annotated[int, Path(gt=0, le=MAX_ID)]


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    if not token:
        raise UnauthorizedError("Not authenticated")
    try:
        user_id = int(decode_token(token)["sub"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise UnauthorizedError() from None
    user = user_repository.get_by_id(db, user_id)
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

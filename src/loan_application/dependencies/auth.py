import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from loan_application.logging_context import user_id_ctx
from loan_application.db import get_db
from loan_application.repositories import user_repositories
from loan_application.security import decode_access_token
from loan_application.tables import User, UserRole
import logging
from fastapi import Request
logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    user = user_repositories.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker

async def authenticated_user(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    user_id_ctx.set(str(user.id))
    logger.info("%s %s role=%s", request.method, request.url.path, user.role.value)
    return user
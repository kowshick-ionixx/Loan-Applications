"""EXTRA API: all /api/users endpoints (not in Round 2 spec / plan up to Week 2
Tuesday). Switched off in main.py; uncomment `app.include_router(users.router)`
there to enable."""

from typing import Annotated

from fastapi import APIRouter, Path

from loan_application.db import MAX_ID, DbSession
from loan_application.dependencies import CurrentUser, OfficerUser
from loan_application.models import User
from loan_application.schemas.common import (
    PROTECTED_RESPONSES,
    MessageResponse,
    error,
)
from loan_application.schemas.user import PasswordChange, RoleUpdate, UserOut
from loan_application.services import user_service

router = APIRouter(prefix="/api/users", tags=["Users"], responses=PROTECTED_RESPONSES)
NOT_FOUND = {404: error("User not found")}
UserId = Annotated[int, Path(gt=0, le=MAX_ID)]


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> User:
    return user


@router.patch(
    "/me/password",
    response_model=MessageResponse,
    responses={400: error("Old password is incorrect, or new password invalid")},
)
def change_my_password(
    data: PasswordChange, db: DbSession, user: CurrentUser
) -> MessageResponse:
    user_service.change_password(db, user, data.old_password, data.new_password)
    return MessageResponse(message="Password changed successfully")


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, user: OfficerUser) -> list[User]:
    """Officers only."""
    return user_service.list_users(db)


@router.get("/{user_id}", response_model=UserOut, responses=NOT_FOUND)
def get_user(user_id: UserId, db: DbSession, user: CurrentUser) -> User:
    """Officers see any user; customers only themselves."""
    return user_service.get_user_for(db, user_id, user)


@router.patch("/{user_id}/role", response_model=UserOut, responses=NOT_FOUND)
def change_role(
    user_id: UserId, data: RoleUpdate, db: DbSession, user: OfficerUser
) -> User:
    """Officers only, and not on themselves. Promoting a customer unlinks their
    customer profile (officers have none); the profile and its loans stay."""
    return user_service.change_role(db, user_id, data.role, user)


@router.delete("/{user_id}", response_model=MessageResponse, responses=NOT_FOUND)
def deactivate_user(
    user_id: UserId, db: DbSession, user: OfficerUser
) -> MessageResponse:
    """Officers only. Soft delete: the user can no longer log in or use a token."""
    user_service.deactivate_user(db, user_id, user)
    return MessageResponse(message="User deactivated successfully")

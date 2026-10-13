from fastapi import HTTPException

from loan_application.tables import User, UserRole


def ensure_can_access_customer(user: User, customer_id: int) -> None:
    if user.role == UserRole.OFFICER:
        return
    if user.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Not allowed to access this resource")
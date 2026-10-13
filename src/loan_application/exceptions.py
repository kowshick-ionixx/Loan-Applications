import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from loan_application.logging_config import request_id_var

logger = logging.getLogger(__name__)

FIELD_MESSAGES = {
    "name": "must be 3-50 characters, letters and spaces only",
    "email": "must be a valid email address",
    "phone": "must be exactly 10 digits",
    "date_of_birth": "must be a past date in YYYY-MM-DD format",
    "monthly_income": "must be greater than 0, max 10 digits and 2 decimals",
    "customer_id": "must be a positive integer",
    "loan_id": "must be a positive integer",
    "amount": "must be between 10000 and 5000000, max 2 decimals",
    "tenure_months": "must be one of 12, 24, 36, 48, 60",
    "status": "must be APPROVED or REJECTED",
    "username": "must be 3-50 characters: letters, digits, _ . or @",
    "password": "must be at least 8 characters",
}


class AppError(Exception):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(401, "UNAUTHORIZED", message)


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid username or password") -> None:
        super().__init__(401, "INVALID_CREDENTIALS", message)


class ForbiddenError(AppError):
    def __init__(
        self, message: str = "You do not have permission to perform this action"
    ) -> None:
        super().__init__(403, "FORBIDDEN", message)


class ProfileRequiredError(AppError):
    def __init__(self) -> None:
        message = "Create your customer profile via POST /api/customers first"
        super().__init__(403, "CUSTOMER_PROFILE_REQUIRED", message)


class ProfileExistsError(AppError):
    def __init__(self) -> None:
        message = "You already have a customer profile"
        super().__init__(409, "PROFILE_ALREADY_EXISTS", message)


class DuplicateUsernameError(AppError):
    def __init__(self, username: str) -> None:
        message = f"Username '{username}' already exists"
        super().__init__(409, "DUPLICATE_USERNAME", message)


def field_message(error: dict) -> str:
    if error["type"] == "missing":
        return "is required"
    return FIELD_MESSAGES.get(str(error["loc"][-1]), str(error["msg"]))


def error_response(
    status_code: int, content: dict, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    content["request_id"] = request_id_var.get()
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    logger.warning("%s: %s", exc.error, exc.message)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return error_response(
        exc.status_code, {"error": exc.error, "message": exc.message}, headers
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    error = HTTPStatus(exc.status_code).name
    logger.warning("%s: %s %s", error, request.method, request.url.path)
    content = {"error": error, "message": exc.detail}
    return error_response(exc.status_code, content, exc.headers)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = exc.errors()
    if any(e["type"] == "json_invalid" or tuple(e["loc"]) == ("body",) for e in errors):
        logger.warning("Invalid request body")
        message = "Request body is missing or is not valid JSON"
        return error_response(400, {"error": "INVALID_REQUEST", "message": message})

    details = [
        {"field": str(e["loc"][-1]), "message": field_message(e)} for e in errors
    ]
    logger.warning("Validation failed: %s", ", ".join(d["field"] for d in details))
    return error_response(400, {"error": "VALIDATION_FAILED", "details": details})

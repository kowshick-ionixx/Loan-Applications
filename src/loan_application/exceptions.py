import logging
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
}


class AppError(Exception):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


def error_response(status_code: int, content: dict, headers=None) -> JSONResponse:
    content["request_id"] = request_id_var.get()
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("%s: %s", exc.error, exc.message)
    return error_response(exc.status_code, {"error": exc.error, "message": exc.message})


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error = HTTPStatus(exc.status_code).name
    logger.warning("%s: %s %s", error, request.method, request.url.path)
    content = {"error": error, "message": exc.detail}
    return error_response(exc.status_code, content, exc.headers)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    if any(e["type"] == "json_invalid" or tuple(e["loc"]) == ("body",) for e in errors):
        logger.warning("Invalid request body")
        message = "Request body is missing or is not valid JSON"
        return error_response(400, {"error": "INVALID_REQUEST", "message": message})

    details = [
        {
            "field": str(e["loc"][-1]),
            "message": (
                "is required"
                if e["type"] == "missing"
                else FIELD_MESSAGES.get(str(e["loc"][-1]), e["msg"])
            ),
        }
        for e in errors
    ]
    logger.warning("Validation failed: %s", ", ".join(d["field"] for d in details))
    return error_response(400, {"error": "VALIDATION_FAILED", "details": details})

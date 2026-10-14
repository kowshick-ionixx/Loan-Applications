import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from loan_application.config import settings
from loan_application.db import DbSession
from loan_application.dependencies import check_token_before_body
from loan_application.exceptions import (
    AppError,
    app_error_handler,
    error_response,
    http_error_handler,
    validation_error_handler,
)
from loan_application.logging_config import (
    coloured_status,
    request_id_var,
    setup_logging,
    user_id_var,
)
from loan_application.routers import auth, customers, loans

# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# from loan_application.routers import users

setup_logging(settings.log_format)
logger = logging.getLogger(__name__)


async def request_validation_error(request: Request, exc: Exception) -> Response:
    try:
        await check_token_before_body(request)
    except AppError as auth_error:
        return await app_error_handler(request, auth_error)
    return await validation_error_handler(request, exc)


app = FastAPI(title="Loan Application Service")
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error)
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(loans.router)
# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.
# app.include_router(users.router)


def openapi_schema() -> dict:
    """Validation errors are answered with 400 (see exceptions.py), never 422,
    so drop FastAPI's default 422 entry from /docs."""
    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for operations in schema["paths"].values():
            for operation in operations.values():
                operation["responses"].pop("422", None)
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = openapi_schema  # type: ignore[method-assign]


@app.middleware("http")
async def request_context(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        user_id_var.set(getattr(request.state, "user_id", None))
        logger.exception("Unhandled error")
        message = "An unexpected error occurred"
        response = error_response(500, {"error": "INTERNAL_ERROR", "message": message})
    ms = (time.perf_counter() - start) * 1000
    user_id_var.set(getattr(request.state, "user_id", None))
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        coloured_status(response.status_code, settings.log_format),
        ms,
    )
    response.headers["X-Request-ID"] = request_id
    request_id_var.reset(token)
    return response


@app.get("/health")
def health(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

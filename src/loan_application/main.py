import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from starlette.exceptions import HTTPException

from loan_application.db import DbSession
from loan_application.exceptions import (
    AppError,
    app_error_handler,
    error_response,
    http_error_handler,
    validation_error_handler,
)
from loan_application.logging_config import request_id_var, setup_logging
from loan_application.routers import customers, loans

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Loan Application Service")
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(customers.router)
app.include_router(loans.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error")
        message = "An unexpected error occurred"
        response = error_response(500, {"error": "INTERNAL_ERROR", "message": message})
    ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        ms,
    )
    response.headers["X-Request-ID"] = request_id
    request_id_var.reset(token)
    return response


@app.get("/health")
def health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

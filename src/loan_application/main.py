from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from loan_application.routers import auth_routers
from loan_application.logging_context import setup_logging

from loan_application.db import get_db
from loan_application.exceptions import ConflictError, InvalidInputError, NotFoundError
from loan_application.routers.customer_routers import router as customers_router
from loan_application.routers.loan_routers import (
    router as loans_router,  # replace the first one so changed name
)
setup_logging()
app = FastAPI(title="Loan Application Service")
app.include_router(loans_router)
app.include_router(customers_router)
app.include_router(auth_routers.router)


@app.get("/health", tags=["Health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")


@app.exception_handler(RequestValidationError)
async def invalid_input_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():  # one entry per failing field
        field = ".".join(str(p) for p in err["loc"][1:]) or "body"
        details.append(
            {
                "field": field,
                "message": err["msg"].removeprefix("Value error, "),
            }
        )

    return JSONResponse(
        status_code=400,
        content={
            "error": "VALIDATION_FAILED",
            "message": "Invalid input",
            "details": details,
        },
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_error_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=400,
        content={"error": "VALIDATION_FAILED", "message": exc.message},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "NOT_FOUND", "message": exc.message},
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(
        status_code=409,
        content={"error": "CONFLICT", "message": exc.message},
    )


HTTP_CODES = { 401: "UNAUTHORIZED",403: "FORBIDDEN",404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 503: "SERVICE_UNAVAILABLE"}


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": HTTP_CODES.get(exc.status_code, "HTTP_ERROR"),
            "message": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(IntegrityError)
async def database_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "error": "CONFLICT",
            "message": "This record already exists or is linked to other data",
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    print("UNEXPECTED ERROR:", repr(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


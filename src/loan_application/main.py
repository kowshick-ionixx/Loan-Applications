from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from loan_application.customer import InvalidInputError, NotFoundError
from loan_application.customer import router as customer_router
from loan_application.exceptions import InvalidInputError, NotFoundError
from loan_application.loan import router as loan_router

app = FastAPI(title="Loan Application Service")
app.include_router(loan_router)
app.include_router(customer_router) 


@app.exception_handler(RequestValidationError)
async def invalid_input_handler(request: Request, exc: RequestValidationError):
    for e in exc.errors():
        if e["type"] == "json_invalid" or tuple(e["loc"]) == ("body",):
            return JSONResponse(status_code=400, content={"error": "INVALID_REQUEST"})
    return JSONResponse(
        status_code=400,
        content={"error": "VALIDATION_FAILED", "message": "Invalid input"},
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


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    print("UNEXPECTED ERROR:", repr(exc))   
    return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR"})
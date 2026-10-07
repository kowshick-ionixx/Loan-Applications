from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from loan_application.db import DbSession
from loan_application.exceptions import AppError
from loan_application.routers import customers

app = FastAPI(title="Loan Application Service")
app.include_router(customers.router)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )


@app.get("/health")
def health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

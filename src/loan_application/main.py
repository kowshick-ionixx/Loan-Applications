from fastapi import FastAPI
from sqlalchemy import text

from loan_application.db import DbSession
from loan_application.exceptions import AppError, app_error_handler
from loan_application.routers import customers

app = FastAPI(title="Loan Application Service")
app.add_exception_handler(AppError, app_error_handler)
app.include_router(customers.router)


@app.get("/health")
def health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


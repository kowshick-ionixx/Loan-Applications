from datetime import date
from decimal import Decimal
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, HTTPException,Request
from sqlalchemy import text,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from loan_application.schemas import CustomerIn, CustomerOut
from loan_application.exceptions import NotFoundError, InvalidInputError
from loan_application.db import get_db
from loan_application.tables import Customer

router=APIRouter(prefix="/customers", tags=["Customers"])











# ---------- health ----------
@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        print("DB ERROR:", e)
        raise HTTPException(status_code=503, detail="database unavailable")

#------ENDPOINTS FOR CUSTOMER CRUD OPERATIONS-------

@router.post("/customers", response_model=CustomerOut, status_code=201)
def add_customer(data: CustomerIn, db: Session = Depends(get_db)):
    exists = db.scalar(select(Customer.id).where(Customer.email == data.email))
    if exists:
        raise HTTPException(status_code=409, detail="Customer with this email already exists")
    customer = Customer(**data.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Customer with this email already exists")
    db.refresh(customer)
    return customer

@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerIn, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer



@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer =  db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()

 


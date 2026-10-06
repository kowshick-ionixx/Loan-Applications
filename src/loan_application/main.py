from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
 
from loan_application.db import get_db
 
app = FastAPI(title="Loan Application Service")
 
 
@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        print("DB ERROR:", e)
        raise HTTPException(status_code=503, detail="database unavailable")

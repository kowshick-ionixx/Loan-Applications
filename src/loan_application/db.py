from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
 
DATABASE_URL = "postgresql+psycopg://kowshick:kowshi123@localhost:5432/app_db"
 
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
 
 
class Base(DeclarativeBase):
    pass
 
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
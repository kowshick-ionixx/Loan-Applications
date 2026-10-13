from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from loan_application.config import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

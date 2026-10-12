import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from loan_application.tables import Base  # adjust if your Base lives elsewhere

engine = create_engine("sqlite:///:memory:")
TestingSession = sessionmaker(bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)

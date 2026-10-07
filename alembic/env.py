import logging

from sqlalchemy import create_engine

import loan_application
from alembic import context
from loan_application.db import DATABASE_URL, Base

logging.basicConfig(level=logging.INFO, format="%(message)s")

engine = create_engine(DATABASE_URL)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()

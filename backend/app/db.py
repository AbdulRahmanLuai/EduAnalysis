from sqlmodel import SQLModel, create_engine, Session
from app.models import *
from app.config import settings

# Database URL
DATABASE_URL = settings.DATABASE_URL

# Create engine
engine = create_engine(DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session

    
from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO)


def get_session():
    with Session(engine) as session:
        yield session

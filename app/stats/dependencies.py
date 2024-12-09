from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import app_settings
from app.stats.models import BaseModel

_engine = create_engine(app_settings.sqlite, connect_args={"check_same_thread": False})
SessionMaker = sessionmaker(_engine)


def _create_session():
    with Session(_engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(_create_session)]


def create_database():
    BaseModel.metadata.create_all(_engine)

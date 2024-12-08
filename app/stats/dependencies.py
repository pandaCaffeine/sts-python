from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import app_settings
from app.stats.models import BaseModel
from app.stats.service import StatService, StatServiceImpl

_engine = create_engine(app_settings.sqlite, connect_args={"check_same_thread": False})


def _create_session():
    with Session(_engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(_create_session)]


def _create_service(session: SessionDep):
    return StatServiceImpl(session)


StatServiceDep = Annotated[StatService, Depends(_create_service)]


def create_database():
    BaseModel.metadata.create_all(_engine)

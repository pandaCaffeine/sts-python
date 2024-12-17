from sts.config import app_settings
from sts.stats.models import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(app_settings.sqlite, connect_args={"check_same_thread": False})
SessionMaker = sessionmaker(_engine)


def create_database():
    BaseModel.metadata.create_all(_engine)

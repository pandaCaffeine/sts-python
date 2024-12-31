from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sts.config import app_settings
from sts.stats.models import BaseModel

_engine = create_async_engine(app_settings.db)
AsyncSessionMaker = async_sessionmaker(_engine)

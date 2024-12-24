import datetime

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from enum import Enum


class BaseModel(DeclarativeBase): pass


class RequestPriorityEnum(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class RequestStat(BaseModel):
    __tablename__ = "request_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(index=True, unique=True)
    hits: Mapped[int] = mapped_column(default=0)
    update_dt: Mapped[datetime.datetime] = mapped_column(sqlalchemy.TIMESTAMP(), default=func.now)
    errors: Mapped[int] = mapped_column(default=0)
    r_priority: Mapped[RequestPriorityEnum] = mapped_column(default=RequestPriorityEnum.LOW)

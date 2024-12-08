import abc
import datetime
from abc import ABC

from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing_extensions import override

from app.stats.models import RequestStat


class StatService(ABC):
    @abc.abstractmethod
    def add_hit(self, path: str):
        pass

    @abc.abstractmethod
    def get_top_requests(self, count: int = 5):
        pass


class StatServiceImpl(StatService):
    _session: Session

    def __init__(self, session: Session):
        self._session = session

    def add_hit(self, path: str) -> None:
        path = path.lower()
        query = select(RequestStat).where(RequestStat.path == path)
        stat = self._session.scalars(query).one_or_none()
        if stat:
            stat.hits += 1
        else:
            stat = RequestStat(path=path, hits=1)
            self._session.add(stat)

        stat.update_dt = datetime.datetime.now(datetime.UTC)
        self._session.commit()

    def get_top_requests(self, count: int = 5) -> set[str]:
        query = select(RequestStat.path).order_by(desc(RequestStat.hits)).limit(count)
        result = self._session.scalars(query).all()
        return set(result)

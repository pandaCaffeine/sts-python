import datetime

from sqlalchemy import select, desc
from sqlalchemy.orm import Session, sessionmaker
from starlette.status import HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_304_NOT_MODIFIED

from app.stats.models import RequestStat


class StatService:
    _session_factory: sessionmaker[Session]

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def _add_hit(self, path: str) -> None:
        query = select(RequestStat).where(RequestStat.path == path)
        with self._session_factory() as session:
            stats = session.scalars(query).one_or_none()
            if stats:
                stats.hits += 1
            else:
                stats = RequestStat(path=path, hits=1)
                session.add(stats)
            stats.update_dt = datetime.datetime.now(datetime.UTC)
            session.commit()

    def _invalidate_hits(self, path: str) -> None:
        with self._session_factory() as session:
            session.query(RequestStat).where(RequestStat.path == path).delete(synchronize_session=False)
            session.commit()

    def handle_request(self, path: str, response_code: int) -> None:
        if response_code == HTTP_404_NOT_FOUND:
            self._invalidate_hits(path)
            return

        if response_code in [HTTP_304_NOT_MODIFIED, HTTP_200_OK]:
            self._add_hit(path)

    def get_top_requests(self, count: int = 5) -> set[str]:
        query = select(RequestStat.path).order_by(desc(RequestStat.hits)).limit(count)
        with self._session_factory() as session:
            result = session.scalars(query).all()
            return set(result)

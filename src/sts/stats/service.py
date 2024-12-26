import datetime

import starlette.status as http_codes
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sts.stats.models import RequestStat


class StatService:
    _session_factory: async_sessionmaker[AsyncSession]

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def _add_hit(self, path: str) -> None:
        query = select(RequestStat).where(RequestStat.path == path)
        async with self._session_factory() as session:
            stats = (await session.scalars(query)).one_or_none()
            if stats:
                stats.hits += 1
            else:
                stats = RequestStat(path=path, hits=1)
                session.add(stats)
            stats.update_dt = datetime.datetime.utcnow()
            await session.commit()

    async def _invalidate_hits(self, path: str) -> None:
        async with self._session_factory() as session:
            query = delete(RequestStat).where(RequestStat.path == path)
            await session.execute(query)
            await session.commit()

    async def handle_request(self, path: str, response_code: int) -> None:
        if response_code == http_codes.HTTP_404_NOT_FOUND:
            await self._invalidate_hits(path)
            return

        if response_code in [http_codes.HTTP_304_NOT_MODIFIED, http_codes.HTTP_200_OK]:
            await self._add_hit(path)

    async def get_top_requests(self, count: int = 5) -> set[str]:
        query = select(RequestStat.path).order_by(desc(RequestStat.hits)).limit(count)
        async with self._session_factory() as session:
            result = (await session.scalars(query)).all()
            return set(result)

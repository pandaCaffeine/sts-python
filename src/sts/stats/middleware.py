from fastapi import Request, BackgroundTasks, Response
from starlette.middleware.base import RequestResponseEndpoint

from sts.config import bucket_map
from sts.stats.dependencies import SessionMaker
from sts.stats.service import StatService


def _get_all_buckets() -> frozenset[str]:
    result = set[str]()
    for i in bucket_map.all_source_buckets:
        result.add(i)

    for i in bucket_map.buckets.keys():
        result.add(i)

    return frozenset(result)


_known_bucket_paths = _get_all_buckets()


async def stats_middleware(request: Request, _next: RequestResponseEndpoint) -> Response:
    response = await _next(request)
    path_segments = [t for t in request.url.path.split('/') if t]

    if len(path_segments) > 0:
        first_fragment = path_segments[0]
        if first_fragment in _known_bucket_paths:
            background_tasks = response.background or BackgroundTasks()
            stats_service = StatService(SessionMaker)
            background_tasks.add_task(stats_service.handle_request, request.url.path, response.status_code)
            response.background = background_tasks

    return response

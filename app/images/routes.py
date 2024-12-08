from typing import Annotated

from fastapi import APIRouter, BackgroundTasks
from fastapi.params import Depends, Header
from starlette.responses import Response

from app.images.dependencies import get_thumbnail_service
from app.images.thumbnail_service import ThumbnailService
from app.stats.dependencies import StatServiceDep

images_router = APIRouter()


@images_router.get("/{bucket}/{file_name}")
def get_thumbnail(bucket: str, file_name: str,
                  thumbnail_service: Annotated[ThumbnailService, Depends(get_thumbnail_service)],
                  stat_service: StatServiceDep, background_task: BackgroundTasks,
                  etag: Annotated[str | None, Header(alias="If-None-Match")] = None) -> Response:
    background_task.add_task(stat_service.add_hit, f"{bucket}/{file_name}")
    return thumbnail_service.get_thumbnail(bucket, file_name, etag)


@images_router.get("/{bucket}/{file_name}/{alias}")
def get_thumbnail_by_alias(bucket: str, file_name: str, alias: str,
                           thumbnail_service: Annotated[ThumbnailService, Depends(get_thumbnail_service)],
                           stat_service: StatServiceDep, background_task: BackgroundTasks,
                           etag: Annotated[str | None, Header(alias="If-None-Match")] = None) -> Response:
    background_task.add_task(stat_service.add_hit, f"{bucket}/{file_name}/{alias}")
    return thumbnail_service.get_thumbnail_by_alias(bucket, file_name, alias, etag)

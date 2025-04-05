from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Header
from starlette.responses import Response

from sts.images.dependencies import ThumbnailServiceDep

images_router = APIRouter()

_EtagDep = Annotated[str | None, Header(alias="If-None-Match")]


@images_router.get("/{bucket}/{file_name}")
async def get_thumbnail(bucket: str, file_name: str,
                  thumbnail_service: ThumbnailServiceDep,
                  etag: _EtagDep = None) -> Response:
    return await thumbnail_service.get_thumbnail(bucket, file_name, etag)


@images_router.get("/{bucket}/{file_name}/{alias}")
async def get_thumbnail_by_alias(bucket: str, file_name: str, alias: str,
                           thumbnail_service: ThumbnailServiceDep,
                           etag: _EtagDep = None) -> Response:
    return await thumbnail_service.get_thumbnail_by_alias(bucket, file_name, alias, etag)

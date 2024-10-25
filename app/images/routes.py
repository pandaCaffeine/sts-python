from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Header
from starlette.responses import Response

from app.images.dependencies import get_thumbnail_service
from app.images.thumbnail_service import ThumbnailService

images_router = APIRouter()


@images_router.get("/{bucket}/{file_name}")
def get_thumbnail(bucket: str, file_name: str,
                  thumbnail_service: Annotated[ThumbnailService, Depends(get_thumbnail_service)],
                  etag: Annotated[str | None, Header(alias="If-None-Match")] = None) -> Response:
    return thumbnail_service.make_thumbnail(bucket, file_name, etag)


@images_router.get("/{bucket}/{file_name}/{alias}")
def get_thumbnail_by_alias(bucket: str, file_name: str, alias: str,
                           thumbnail_service: Annotated[ThumbnailService, Depends(get_thumbnail_service)],
                           etag: Annotated[str | None, Header(alias="If-None-Match")] = None) -> Response:
    return thumbnail_service.make_thumbnail_by_alias(bucket, file_name, alias, etag)

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaSyncRoute
from fastapi import APIRouter, Header, Response

from sts.images.service import ThumbnailService

images_router = APIRouter(route_class=DishkaSyncRoute)

_EtagDep = Annotated[str | None, Header(alias="If-None-Match")]


@images_router.get("/{bucket}/{file_name}")
def get_thumbnail(bucket: str, file_name: str,
                  thumbnail_service: FromDishka[ThumbnailService],
                  etag: _EtagDep = None) -> Response:
    return thumbnail_service.get_thumbnail(bucket, file_name, etag)


@images_router.get("/{bucket}/{file_name}/{alias}")
def get_thumbnail_by_alias(bucket: str, file_name: str, alias: str,
                           thumbnail_service: FromDishka[ThumbnailService],
                           etag: _EtagDep = None) -> Response:
    return thumbnail_service.get_thumbnail_by_alias(bucket, file_name, alias, etag)

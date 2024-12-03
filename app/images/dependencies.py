import logging
from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from loguru import logger
from minio import Minio
from pydantic import HttpUrl

from app.config import BucketsMap, S3Settings, AppSettings
from app.dependencies import get_buckets_map, get_app_settings
from app.images.storage_client import StorageClient, S3StorageClient
from app.images.thumbnail_service import ThumbnailService


def _parse_path(path: str) -> (str, str | None):
    assert path, "path is required"
    fragments: list[str] = [t for t in path.split('/') if t]
    if len(fragments) > 1:
        return fragments[0], fragments[1]
    return fragments[0], None


@lru_cache
def get_minio_client(app_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> Minio:
    s3_settings = app_settings.s3

    if isinstance(app_settings.s3, HttpUrl):
        s3_url: HttpUrl = app_settings.s3
        region, source_bucket = _parse_path(s3_url.path)
        s3_settings = S3Settings(
            endpoint=f"{s3_url.host}:{s3_url.port}", access_key=s3_url.username,
            secret_key=s3_url.password, region=region, trust_cert=s3_url.scheme == 'https',
            use_tsl=s3_url.scheme == 'https'
        )

    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


@lru_cache
def get_storage_client(minio: Annotated[Minio, Depends(get_minio_client)]) -> StorageClient:
    return S3StorageClient(minio)


def get_request_logger(bucket: str, file_name: str):
    return logger.bind(bucket=bucket, file_name=file_name)


def get_thumbnail_service(storage_client: Annotated[StorageClient, Depends(get_storage_client)],
                          buckets_map: Annotated[BucketsMap, Depends(get_buckets_map)],
                          request_logger: Annotated[logging.Logger, Depends(get_request_logger)]) -> ThumbnailService:
    return ThumbnailService(storage_client, buckets_map, request_logger)

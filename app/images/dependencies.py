import logging
from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from loguru import logger
from minio import Minio

from app.config import app_settings, bucket_map
from app.images.storage_client import StorageClient, S3StorageClient
from app.images.thumbnail_service import ThumbnailService


def _parse_path(path: str) -> (str, str | None):
    assert path, "path is required"
    fragments: list[str] = [t for t in path.split('/') if t]
    if len(fragments) > 1:
        return fragments[0], fragments[1]
    return fragments[0], None


@lru_cache
def get_minio_client() -> Minio:
    s3_settings = app_settings.s3
    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


@lru_cache
def get_storage_client(minio: Annotated[Minio, Depends(get_minio_client)]) -> StorageClient:
    return S3StorageClient(minio)


def get_request_logger(bucket: str, file_name: str):
    return logger.bind(bucket=bucket, file_name=file_name)


def get_thumbnail_service(storage_client: Annotated[StorageClient, Depends(get_storage_client)],
                          request_logger: Annotated[logging.Logger, Depends(get_request_logger)]) -> ThumbnailService:
    return ThumbnailService(storage_client, bucket_map, request_logger)

from functools import lru_cache
from typing import Annotated

from logging import Logger
from fastapi.params import Depends
from loguru import logger
from minio import Minio

from sts.config import get_app_settings, get_buckets_map
from sts.images.file_storage_scanner import FileStorageScanner, FileStorageScannerImpl
from sts.images.storage_client import StorageClient, S3StorageClient
from sts.images.thumbnail_service import ThumbnailService


@lru_cache
def _get_minio_client() -> Minio:
    s3_settings = get_app_settings().s3
    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


@lru_cache
def get_storage_client() -> StorageClient:
    minio_client = _get_minio_client()
    return S3StorageClient(minio_client)


StorageClientDep = Annotated[StorageClient, Depends(get_storage_client)]


def _get_request_logger(bucket: str, file_name: str) -> Logger:
    return logger.bind(bucket=bucket, file_name=file_name)  # type: ignore


RequestLoggerDep = Annotated[Logger, Depends(_get_request_logger)]


def _get_file_storage_scanner(storage_client: StorageClientDep) -> FileStorageScanner:
    return FileStorageScannerImpl(storage_client, get_buckets_map())


FileStorageScannerDep = Annotated[FileStorageScanner, Depends(_get_file_storage_scanner)]


def _get_thumbnail_service(storage_client: StorageClientDep,
                           request_logger: RequestLoggerDep,
                           file_storage_scanner: FileStorageScannerDep) -> ThumbnailService:
    return ThumbnailService(storage_client, file_storage_scanner, request_logger)


ThumbnailServiceDep = Annotated[ThumbnailService, Depends(_get_thumbnail_service)]

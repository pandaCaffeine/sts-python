from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from loguru import Logger
from minio import Minio

from app.config import AppSettings, S3Settings, BucketSettings
from app.images.thumbnail_service import ThumbnailService
from app.images.storage_client import StorageClient, S3StorageClient
from app.dependencies import get_app_settings, get_request_logger


@lru_cache
def get_s3_connection_settings(
        global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> S3Settings:
    return global_settings.s3


@lru_cache
def get_default_source_bucket(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> str:
    return global_settings.source_bucket


@lru_cache
def get_buckets_settings(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> dict[
    str, BucketSettings]:
    return global_settings.buckets


@lru_cache
def get_minio_client(s3_settings: Annotated[S3Settings, Depends(get_s3_connection_settings)]) -> Minio:
    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


@lru_cache
def get_storage_client(minio: Annotated[Minio, Depends(get_minio_client)]) -> StorageClient:
    return S3StorageClient(minio)


@lru_cache
def get_source_buckets(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> set[str]:
    result = [s.source_bucket for s in global_settings.buckets.values() if s.source_bucket is not None]
    result.append(global_settings.source_bucket)

    return set(result)


@lru_cache
def get_default_bucket(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> str:
    return global_settings.source_bucket


@lru_cache
def get_alias_map(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> dict[str, str]:
    result = dict[str, str]()
    for bucket_name, bucket_cfg in global_settings.buckets.items():
        if bucket_cfg.alias is None:
            continue
        result[bucket_cfg.alias] = bucket_name
    return result


def get_thumbnail_service(storage_client: Annotated[StorageClient, Depends(get_storage_client)],
                          buckets_map: Annotated[dict[str, BucketSettings], Depends(get_buckets_settings)],
                          source_bucket: Annotated[str, Depends(get_default_bucket)],
                          all_source_buckets: Annotated[set[str], Depends(get_source_buckets)],
                          alias_map: Annotated[dict[str, str], Depends(get_alias_map)],
                          logs: Annotated[Logger, Depends(get_request_logger)]) -> ThumbnailService:
    return ThumbnailService(storage_client, buckets_map, source_bucket, all_source_buckets, alias_map, logs)

from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from minio import Minio

from app.config import S3Settings, BucketSettings, app_settings
from app.images.storage_client import StorageClient, S3StorageClient
from app.images.thumbnail_service import ThumbnailService


def get_s3_connection_settings() -> S3Settings:
    return app_settings.s3


def get_buckets_settings() -> dict[
    str, BucketSettings]:
    return app_settings.buckets


@lru_cache
def get_minio_client() -> Minio:
    s3_settings = app_settings.s3
    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


@lru_cache
def get_storage_client(minio: Annotated[Minio, Depends(get_minio_client)]) -> StorageClient:
    return S3StorageClient(minio)


@lru_cache
def get_source_buckets() -> set[str]:
    result = [s.source_bucket for s in app_settings.buckets.values() if s.source_bucket is not None]
    result.append(app_settings.source_bucket)

    return set(result)


@lru_cache
def get_default_bucket() -> str:
    return app_settings.source_bucket


@lru_cache
def get_alias_map() -> dict[str, str]:
    result = dict[str, str]()
    for bucket_name, bucket_cfg in app_settings.buckets.items():
        if bucket_cfg.alias is None:
            continue
        result[bucket_cfg.alias] = bucket_name
    return result


def get_thumbnail_service(storage_client: Annotated[StorageClient, Depends(get_storage_client)],
                          buckets_map: Annotated[dict[str, BucketSettings], Depends(get_buckets_settings)],
                          source_bucket: Annotated[str, Depends(get_default_bucket)],
                          all_source_buckets: Annotated[set[str], Depends(get_source_buckets)],
                          alias_map: Annotated[dict[str, str], Depends(get_alias_map)]) -> ThumbnailService:
    return ThumbnailService(storage_client, buckets_map, source_bucket, all_source_buckets, alias_map)

from logging import Logger
from minio import S3Error
from itertools import chain

import sts.logs
from sts.buckets.service import BucketService
from sts.config import AppSettings
from sts.file_storage.client import FileStorageClient
from sts.models.enums import BucketStatus
from sts.models.bucket import BucketsInfo


class MinioBucketService(BucketService):
    _app_settings: AppSettings
    _storage_client: FileStorageClient
    _logger: sts.logs.ILogger

    def __init__(self, app_settings: AppSettings, storage_client: FileStorageClient, l: sts.logs.ILogger):
        self._app_settings = app_settings
        self._storage_client = storage_client
        self._logger = l

    def _create_bucket(self, bucket_name: str, life_time_days: int) -> BucketStatus:
        try:
            bucket_created = self._storage_client.try_create_bucket(bucket_name, life_time_days)
            if bucket_created:
                self._logger.info(
                    f"Bucket {bucket_name} was created with life time in {life_time_days} days (zero days means infinity)")
                return BucketStatus.created
            else:
                self._logger.info(f"Bucket {bucket_name} already exists, skip it")
                return BucketStatus.exists
        except (S3Error, Exception) as e:
            self._logger.warning(f"Failed to create bucket {bucket_name}", exc_info=e)
            return BucketStatus.error

    def create_buckets(self) -> BucketsInfo:
        self._logger.debug(f"Creating {len(self._app_settings.buckets)} buckets")

        if len(self._app_settings.buckets) == 0:
            self._logger.warning("No buckets were configured, skip it")
            return BucketsInfo()

        source_buckets = dict[str, BucketStatus]()
        thumbnail_buckets = dict[str, BucketStatus]()
        default_source_bucket = self._app_settings.source_bucket
        if default_source_bucket:
            source_buckets[default_source_bucket] = self._create_bucket(default_source_bucket, 0)

        for bucket_name, bucket_settings in self._app_settings.buckets.items():
            life_time_days = self._app_settings.buckets[bucket_name].life_time_days
            thumbnail_buckets[bucket_name] = self._create_bucket(bucket_name, life_time_days)

            source_bucket = bucket_settings.source_bucket
            if source_bucket and source_bucket != default_source_bucket:
                source_buckets[source_bucket] = self._create_bucket(bucket_settings.source_bucket, 0)

        bucket_status_collection = chain(thumbnail_buckets.values(), source_buckets.values())
        error = any(t == BucketStatus.error for t in bucket_status_collection)
        return BucketsInfo(source_buckets=source_buckets, thumbnail_buckets=thumbnail_buckets, error=error)

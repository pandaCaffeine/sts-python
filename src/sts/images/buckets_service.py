from logging import Logger

from minio import S3Error

from sts.config import AppSettings
from sts.images.storage_client import StorageClient
from sts.models import BucketStatus, BucketsInfo


class BucketsService:
    _app_settings: AppSettings
    _storage_client: StorageClient
    _logger: Logger

    def __init__(self, app_settings: AppSettings, storage_client: StorageClient, l: Logger):
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

    @staticmethod
    def _check_if_result_has_errors(result: BucketsInfo) -> bool:
        source_buckets_have_errors = any(t == BucketStatus.error for t in result.source_buckets.items())
        thumbnail_buckets_have_errors = any(t == BucketStatus.error for t in result.thumbnail_buckets.items())
        return source_buckets_have_errors or thumbnail_buckets_have_errors

    def create_buckets(self) -> BucketsInfo:
        self._logger.debug(f"Creating {len(self._app_settings.buckets)} buckets")
        result = BucketsInfo(thumbnail_buckets=dict(), source_buckets=dict(), error=True)

        if len(self._app_settings.buckets) == 0:
            self._logger.warning("No buckets were configured, skip it")
            return result

        default_source_bucket = self._app_settings.source_bucket
        if default_source_bucket:
            result.source_buckets[default_source_bucket] = self._create_bucket(default_source_bucket, 0)

        for bucket_name, bucket_settings in self._app_settings.buckets.items():
            life_time_days = self._app_settings.buckets[bucket_name].life_time_days
            result.thumbnail_buckets[bucket_name] = self._create_bucket(bucket_name, life_time_days)

            source_bucket = bucket_settings.source_bucket
            if source_bucket and source_bucket != default_source_bucket:
                result.source_buckets[source_bucket] = self._create_bucket(bucket_settings.source_bucket, 0)

        result.error = self._check_if_result_has_errors(result)
        return result

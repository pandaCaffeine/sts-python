from logging import Logger

from minio import S3Error

from app.config import AppSettings
from app.images.models import BucketStatus, BucketsInfo
from app.images.storage_client import StorageClient


class BucketsService:
    __app_settings: AppSettings
    __storage_client: StorageClient
    __logger: Logger

    def __init__(self, app_settings: AppSettings, storage_client: StorageClient, logger: Logger):
        self.__app_settings = app_settings
        self.__storage_client = storage_client
        self.__logger = logger

    def __create_bucket(self, bucket_name: str, life_time_days: int) -> BucketStatus:
        try:
            bucket_created = self.__storage_client.try_create_dir(bucket_name, life_time_days)
            if bucket_created:
                self.__logger.info(
                    f"Bucket {bucket_name} was created with life time in {life_time_days} days (zero days means infinity)")
                return BucketStatus.created
            else:
                self.__logger.info(f"Bucket {bucket_name} already exists, skip it")
                return BucketStatus.exists
        except (S3Error, Exception):
            self.__logger.warning(f"Failed to create bucket {bucket_name}", exc_info=True)
            return BucketStatus.error

    def create_buckets(self) -> BucketsInfo:
        self.__logger.debug(f"Creating {len(self.__app_settings.buckets)} buckets")
        result = BucketsInfo(thumbnail_buckets=dict(), source_buckets=dict())

        if len(self.__app_settings.buckets) == 0:
            self.__logger.warning("No buckets were configured, skip it")
            return result

        default_source_bucket = self.__app_settings.source_bucket
        result.source_buckets[default_source_bucket] = self.__create_bucket(default_source_bucket, 0)

        for bucket_name, bucket_settings in self.__app_settings.buckets.items():
            life_time_days = self.__app_settings.buckets[bucket_name].life_time_days
            result.thumbnail_buckets[bucket_name] = self.__create_bucket(bucket_name, life_time_days)

            source_bucket = bucket_settings.source_bucket
            if source_bucket and source_bucket != default_source_bucket:
                result.source_buckets[source_bucket] = self.__create_bucket(bucket_settings.source_bucket, 0)

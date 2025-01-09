from abc import ABC, abstractmethod
from enum import Enum

from sts.config import BucketsMap, BucketSettings
from sts.images.storage_client import StorageClient


class ScanResult(Enum):
    BUCKET_NOT_FOUND = 1
    SOURCE_FILE_NOT_FOUND = 2
    USE_SOURCE_FILE = 3
    FILE_FOUND = 4
    CREATE_NEW = 5


class FileStorageScanner(ABC):

    @abstractmethod
    def scan_file(self, bucket: str, file_name) -> ScanResult:
        pass


class FileStorageScannerImp(FileStorageScanner):
    _storage_client: StorageClient
    _buckets_map: BucketsMap

    def __init__(self, storage_client: StorageClient, buckets_map: BucketsMap):
        assert storage_client, "storage_client is required"
        assert buckets_map, "buckets_map is required"

        self._storage_client = storage_client
        self._buckets_map = buckets_map

    def scan_file(self, bucket: str, file_name) -> ScanResult:
        bucket_settings = self._get_bucket_settings(bucket)
        if not bucket_settings:
            return ScanResult.BUCKET_NOT_FOUND

        source_file_stat = self._storage_client.get_file_stat(bucket, file_name)
        if not source_file_stat:
            return ScanResult.SOURCE_FILE_NOT_FOUND

        if bucket == bucket_settings.source_bucket:
            return ScanResult.USE_SOURCE_FILE

        thumbnail_stat = self._storage_client.get_file_stat(bucket, file_name)
        if thumbnail_stat and thumbnail_stat.parent_etag == source_file_stat.etag:
            return ScanResult.FILE_FOUND

        return ScanResult.CREATE_NEW

    def _get_bucket_settings(self, bucket: str) -> BucketSettings | None:
        if bucket == self._buckets_map.source_bucket:
            return self._buckets_map.buckets[bucket]

        return self._buckets_map.buckets.get(bucket, None)

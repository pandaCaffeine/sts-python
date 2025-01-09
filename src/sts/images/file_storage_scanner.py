from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from sts.config import BucketsMap, BucketSettings
from sts.images.storage_client import StorageClient, StorageFileItem


class ScanStatus(Enum):
    BUCKET_NOT_FOUND = 1
    SOURCE_FILE_NOT_FOUND = 2
    USE_SOURCE_FILE = 3
    FILE_FOUND = 4
    CREATE_NEW = 5


@dataclass(frozen=True, slots=True)
class ScanResult:
    status: ScanStatus = ScanStatus.BUCKET_NOT_FOUND
    source_file_stat: StorageFileItem | None = None
    file_stat: StorageFileItem | None = None
    bucket_settings: BucketSettings | None = None


class FileStorageScanner(ABC):

    @abstractmethod
    def scan_file(self, bucket: str, file_name) -> ScanResult:
        pass

    @abstractmethod
    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        pass


class FileStorageScannerImp(FileStorageScanner):
    _storage_client: StorageClient
    _buckets_map: BucketsMap

    def __init__(self, storage_client: StorageClient, buckets_map: BucketsMap):
        assert storage_client, "storage_client is required"
        assert buckets_map, "buckets_map is required"

        self._storage_client = storage_client
        self._buckets_map = buckets_map

    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        if not source_bucket in self._buckets_map.all_source_buckets:
            result: str | None = None
        else:
            result = self._buckets_map.alias_map.get(alias, source_bucket)

        return result

    def scan_file(self, bucket: str, file_name) -> ScanResult:
        bucket_settings = self._get_bucket_settings(bucket)
        if not bucket_settings:
            return ScanResult(status=ScanStatus.BUCKET_NOT_FOUND)

        source_file_stat = self._storage_client.get_file_stat(bucket_settings.source_bucket, file_name)
        if not source_file_stat:
            return ScanResult(status=ScanStatus.SOURCE_FILE_NOT_FOUND)

        if bucket == bucket_settings.source_bucket:
            return ScanResult(status=ScanStatus.USE_SOURCE_FILE, source_file_stat=source_file_stat)

        thumbnail_stat = self._storage_client.get_file_stat(bucket, file_name)
        if thumbnail_stat and thumbnail_stat.parent_etag == source_file_stat.etag:
            return ScanResult(status=ScanStatus.FILE_FOUND, source_file_stat=source_file_stat, file_stat=thumbnail_stat)

        return ScanResult(status=ScanStatus.CREATE_NEW, source_file_stat=source_file_stat,
                          bucket_settings=bucket_settings)

    def _get_bucket_settings(self, bucket: str) -> BucketSettings | None:
        if bucket == self._buckets_map.source_bucket:
            return self._buckets_map.buckets[bucket]

        return self._buckets_map.buckets.get(bucket, None)

"""MinIO implementation of file storage scanner."""

from sts.config import BucketsMap, BucketSettings
from sts.file_storage.client import FileStorageClient
from sts.file_storage.scanner import FileStorageScanner
from sts.models.enums import ScanStatus
from sts.models.file_storage import ScanResult, StorageFileItem


class MinioFileStorageScanner(FileStorageScanner):
    """Scans MinIO buckets to find or create thumbnails based on source file ETag."""

    # Pre-allocated constants for empty statuses to reduce object creation on frequent hits
    _NOT_FOUND_BUCKET = ScanResult(status=ScanStatus.BUCKET_NOT_FOUND)
    _NOT_FOUND_FILE = ScanResult(status=ScanStatus.SOURCE_FILE_NOT_FOUND)

    _storage_client: FileStorageClient
    _buckets_map: BucketsMap

    def __init__(self, storage_client: FileStorageClient, buckets_map: BucketsMap):
        if storage_client is None:
            raise ValueError("storage_client is required")
        if buckets_map is None:
            raise ValueError("buckets_map is required")

        self._storage_client = storage_client
        self._buckets_map = buckets_map

    # --- Public API --

    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        """Finds bucket by alias within source bucket context."""
        if not source_bucket in self._buckets_map.all_source_buckets:
            return None

        return self._buckets_map.alias_map.get(alias, source_bucket)

    def scan_file(self, bucket: str, file_name: str) -> ScanResult:
        """Determines if thumbnail exists, needs creation, or should use source file directly."""
        bucket_settings = self._buckets_map.buckets.get(bucket)
        if not bucket_settings:
            return self._NOT_FOUND_BUCKET

        source_stat = self._storage_client.get_file_stat(bucket_settings.source_bucket, file_name)
        if not source_stat:
            return self._NOT_FOUND_FILE

        return self._determine_result(bucket, file_name, source_stat, bucket_settings)

    # --- Logic Helpers ---

    def _determine_result(self,
                          bucket: str,
                          file_name: str,
                          source_stat: StorageFileItem,
                          bucket_settings: BucketSettings) -> ScanResult:
        """Core logic for determining the thumbnail state based on bucket relationships."""
        # If the requested bucket is the source bucket itself, we just use the source
        if bucket == bucket_settings.source_bucket:
            return self._use_source_file(source_stat)

        thumb = self._storage_client.get_file_stat(bucket, file_name)
        if thumb and thumb.parent_etag == source_stat.etag:
            return self._file_found(source_stat, thumb)

        return self._create_new(source_stat, bucket_settings)

    # --- Static Factories for ScanResult ---

    @staticmethod
    def _use_source_file(stat: StorageFileItem) -> ScanResult:
        return ScanResult(status=ScanStatus.USE_SOURCE_FILE, source_file_stat=stat)

    @staticmethod
    def _file_found(source: StorageFileItem, thumb: StorageFileItem) -> ScanResult:
        return ScanResult(status=ScanStatus.FILE_FOUND, source_file_stat=source, file_stat=thumb)

    @staticmethod
    def _create_new(source: StorageFileItem, bucket: BucketSettings) -> ScanResult:
        return ScanResult(status=ScanStatus.CREATE_NEW, source_file_stat=source, bucket_settings=bucket)

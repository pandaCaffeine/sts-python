"""
MinIO implementation of file storage scanner.

Provides file scanning capabilities for MinIO-backed storage,
including bucket alias resolution and thumbnail status detection.
"""

from sts.config import BucketsMap, BucketSettings
from sts.file_storage.client import FileStorageClient
from sts.file_storage.scanner import FileStorageScanner
from sts.models.enums import ScanStatus
from sts.models.file_storage import ScanResult, StorageFileItem

# Some inner helper methods and fields
_BUCKET_NOT_FOUND = ScanResult(status=ScanStatus.BUCKET_NOT_FOUND)
_FILE_NOT_FOUND = ScanResult(status=ScanStatus.SOURCE_FILE_NOT_FOUND)


def _use_source_file(source_file_stat: StorageFileItem) -> ScanResult:
    return ScanResult(status=ScanStatus.USE_SOURCE_FILE, source_file_stat=source_file_stat)


def _file_found(source_file_stat: StorageFileItem, file_stat: StorageFileItem) -> ScanResult:
    return ScanResult(status=ScanStatus.FILE_FOUND, source_file_stat=source_file_stat, file_stat=file_stat)


def _create_new_file(source_file_stat: StorageFileItem, bucket: BucketSettings) -> ScanResult:
    return ScanResult(status=ScanStatus.CREATE_NEW, source_file_stat=source_file_stat, bucket_settings=bucket)


class MinioFileStorageScanner(FileStorageScanner):
    """
    File storage scanner implementation for MinIO.

    Scans buckets to determine if thumbnails need to be created
    or can be reused based on source file etag.
    """

    _storage_client: FileStorageClient
    _buckets_map: BucketsMap

    def __init__(self, storage_client: FileStorageClient, buckets_map: BucketsMap):
        if storage_client is None:
            raise ValueError("storage_client is required")
        if buckets_map is None:
            raise ValueError("buckets_map is required")

        self._storage_client = storage_client
        self._buckets_map = buckets_map

    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        """
        Find bucket by alias within source bucket context.

        Args:
            source_bucket: The source bucket name to validate against.
            alias: The alias to look up.

        Returns:
            Resolved bucket name or None if source_bucket is not a valid source.
        """
        if not source_bucket in self._buckets_map.all_source_buckets:
            return None

        return self._buckets_map.alias_map.get(alias, source_bucket)

    def scan_file(self, bucket: str, file_name: str) -> ScanResult:
        """
        Scan for thumbnail file status.

        Determines whether thumbnail exists, needs creation,
        or should use source file directly.

        Args:
            bucket: Target bucket to check.
            file_name: Name of the file to scan.

        Returns:
            ScanResult with status and file information.
        """
        bucket_settings = self._get_bucket_settings(bucket)
        if not bucket_settings:
            return _BUCKET_NOT_FOUND

        source_stat = self._storage_client.get_file_stat(bucket_settings.source_bucket, file_name)
        if not source_stat:
            return _FILE_NOT_FOUND

        return self._determine_scan_result(bucket, file_name, source_stat, bucket_settings)

    def _determine_scan_result(self,
                               bucket: str,
                               file_name: str,
                               source_stat: StorageFileItem,
                               bucket_settings: BucketSettings) -> ScanResult:
        """Determine final scan result based on bucket type and thumbnail state."""
        if bucket == bucket_settings.source_bucket:
            return _use_source_file(source_stat)

        thumbnail_stat = self._storage_client.get_file_stat(bucket, file_name)
        if thumbnail_stat and thumbnail_stat.parent_etag == source_stat.etag:
            return _file_found(source_stat, thumbnail_stat)

        return _create_new_file(source_stat, bucket_settings)

    def _get_bucket_settings(self, bucket: str) -> BucketSettings | None:
        """Get bucket settings for given bucket name."""
        return self._buckets_map.buckets.get(bucket)

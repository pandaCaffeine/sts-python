from abc import ABC, abstractmethod

from sts.models.file_storage import ScanResult


class FileStorageScanner(ABC):
    """Abstract interface for file storage scanning."""

    @abstractmethod
    def scan_file(self, bucket: str, file_name: str) -> ScanResult:
        """Scan for thumbnail file status. Returns whether it exists, needs creation, or should use source."""
        ...

    @abstractmethod
    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        """Resolves a bucket alias to an actual bucket name within a source context."""
        ...

from abc import ABC, abstractmethod

from sts.models.file_storage import ScanResult


class FileStorageScanner(ABC):

    @abstractmethod
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
        pass

    @abstractmethod
    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        """
        Find bucket by alias within source bucket context.

        Args:
            source_bucket: The source bucket name to validate against.
            alias: The alias to look up.

        Returns:
            Resolved bucket name or None if source_bucket is not a valid source.
        """
        pass

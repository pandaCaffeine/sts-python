from abc import ABC, abstractmethod

from sts.models.file_storage import ScanResult


class FileStorageScanner(ABC):

    @abstractmethod
    def scan_file(self, bucket: str, file_name) -> ScanResult:
        pass

    @abstractmethod
    def find_bucket_by_alias(self, source_bucket: str, alias: str) -> str | None:
        pass

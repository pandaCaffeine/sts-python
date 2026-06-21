from typing import Union

from pydantic.dataclasses import dataclass

from sts.config import BucketSettings
from sts.models.file_storage.storage_item import StorageFileItem


@dataclass(frozen=True, slots=True)
class ScanResultNotFound:
    """Bucket or file was not found in the configured buckets."""
    reason: str

@dataclass(frozen=True, slots=True)
class ScanResultUseSourceFile:
    """Source file exists and should be served directly."""
    source_file_stat: StorageFileItem

@dataclass(frozen=True, slots=True)
class ScanResultFileFound:
    """Existing thumbnail was found and its etag matches the source."""
    source_file_stat: StorageFileItem
    file_stat: StorageFileItem

@dataclass(frozen=True, slots=True)
class ScanResultCreateNew:
    """Thumbnail needs creation or overwrite."""
    source_file_stat: StorageFileItem
    bucket_settings: BucketSettings

ScanResult = Union[
    ScanResultNotFound,
    ScanResultUseSourceFile,
    ScanResultFileFound,
    ScanResultCreateNew,
]



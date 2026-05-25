from abc import ABC, abstractmethod
from io import BytesIO
from typing import Iterable
from typing import Union

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from sts.config import BucketSettings


@dataclass(frozen=True, slots=True)
class StorageFileItem:
    """
    Contains file's information
    """
    bucket: str
    """ File location """
    file_name: str
    """ File name """
    size: int
    """ File size """
    content_type: str
    """ Content type """
    etag: str
    """ File's Etag """
    parent_etag: str | None = None
    """ File's metadata """


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


class StorageResponse(ABC):

    def iter_content(self, chunk_size: int = 1024 * 512) -> Iterable[bytes]:
        ...


    @abstractmethod
    def close(self):
        ...

    @property
    @abstractmethod
    def content_length(self) -> int:
        ...

    @property
    @abstractmethod
    def content_type(self) -> str:
        ...

    @property
    @abstractmethod
    def etag(self) -> str:
        ...


@dataclass(frozen=True, slots=True, config=ConfigDict(arbitrary_types_allowed=True))
class ImageData:
    content_type: str
    error: Exception | None = None
    data: BytesIO | None = None

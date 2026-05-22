from abc import ABC, abstractmethod
from io import BytesIO
from typing import Iterable

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from sts.config import BucketSettings
from sts.models.enums import ScanStatus


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
class ScanResult:
    """ File scan result """

    status: ScanStatus = ScanStatus.BUCKET_NOT_FOUND
    """ File status """
    source_file_stat: StorageFileItem | None = None
    """ File stats of the source file if present """
    file_stat: StorageFileItem | None = None
    """ File stats of the file if it was found """
    bucket_settings: BucketSettings | None = None
    """ Bucket settings from config which contains found file """


class StorageResponse(ABC):
    @abstractmethod
    def __enter__(self) -> Iterable[bytes]:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def read_to_end(self) -> Iterable[bytes]:
        pass

    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def content_length(self) -> int:
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        pass

    @property
    @abstractmethod
    def etag(self) -> str:
        pass


@dataclass(frozen=True, slots=True, config=ConfigDict(arbitrary_types_allowed=True))
class ImageData:
    content_type: str
    error: Exception | None = None
    data: BytesIO | None = None

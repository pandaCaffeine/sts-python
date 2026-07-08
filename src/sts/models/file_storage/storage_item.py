from abc import ABC, abstractmethod
from typing import Iterable

from pydantic.dataclasses import dataclass


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


class StorageResponse(ABC):

    @abstractmethod
    def iter_content(self, chunk_size: int = 1024 * 512) -> Iterable[bytes]:
        """Yields file content in configured chunk size."""
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

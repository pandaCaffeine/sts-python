from abc import ABC, abstractmethod
from io import BytesIO

from sts.models.file_storage import StorageFileItem, StorageResponse


class FileStorageClient(ABC):
    """An abstract interface to storage client."""

    # --- Reading ---

    @abstractmethod
    def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        """
        Returns file stats.

        Args:
            bucket: File's bucket.
            file_name: File name.

        Returns:
            :class:`StorageFileItem` or ``None`` if file was not found.
        """
        ...

    @abstractmethod
    def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        """
        Opens stream to read bytes.

        Args:
            bucket: File's bucket.
            file_name: File name.

        Returns:
            :class:`StorageResponse` or ``None`` if file was not found.
        """
        ...

    @abstractmethod
    def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        """
        Loads the given file into memory as :class:`BytesIO`.

        Args:
            bucket: File's bucket.
            file_name: File name.

        Returns:
            :class:`BytesIO` with loaded bytes, or ``None`` if file was not found.
        """
        ...

    # --- Writing ---

    @abstractmethod
    def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True, parent_etag: str | None = None) -> StorageFileItem:
        """
        Uploads file to storage.

        Args:
            bucket: Destination bucket.
            file_name: Destination file name.
            content: Content.
            content_type: Destination content type.
            reset_content: Set ``True`` to reset source content to the beginning.
            parent_etag: File's optional parent etag.

        Returns:
            :class:`StorageFileItem` with upload result.
        """
        ...

    # --- Bucket management ---

    @abstractmethod
    def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        """
        Create bucket if it doesn't exist.

        Args:
            bucket: Bucket name.
            life_time_days: How many days files in the bucket live.

        Returns:
            ``True`` if bucket was created, ``False`` if bucket already exists.
        """
        ...

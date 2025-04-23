from abc import ABC, abstractmethod
from io import BytesIO

from sts.models.file_storage import StorageFileItem, StorageResponse


class FileStorageClient(ABC):
    """
    An abstract interface to storage client
    """

    @abstractmethod
    def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        """
        Returns files stats (:class:`StorageItem`)
        :param bucket: File's bucket
        :param file_name: File name
        :return: :class:`StorageItem` or `None` if file was not found
        """
        pass

    @abstractmethod
    def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        """
        Opens stream to read bytes
        :param bucket: File's bucket
        :param file_name: File name
        :return: Bytes or None if file was not found
        """
        pass

    @abstractmethod
    def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        """
        Loads the given file into memory as :class:`BytesIO`
        :param bucket: File's bucket
        :param file_name: File name
        :return: :class:`BytesIO` with loaded bytes, returns `None` if file was not found
        """
        pass

    @abstractmethod
    def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True, parent_etag: str | None = None) -> StorageFileItem:
        """
        Uploads files to storage
        :param bucket: Destination bucket
        :param file_name: Destination file name
        :param content: Content
        :param content_type: Destination content_type
        :param reset_content: Set true to reset source content to the beginning
        :param parent_etag: File's optional parent etag
        :return: Upload bytes count - size of the content
        """
        pass

    @abstractmethod
    def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        """
        Tries to create bucket in storage
        :param life_time_days: How many days files in the bucket live, in days
        :param bucket: Bucket name
        :return: True if bucket was created, False if bucket already exists
        """
        pass

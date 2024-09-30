import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO

from minio import Minio, S3Error
from urllib3 import BaseHTTPResponse


@dataclass
class StorageItem:
    directory: str
    """ File location """
    name: str
    """ File name """
    size: int
    """ File size """
    content_type: str
    """ Content type """
    etag: str
    """ File's Etag """

    def __init__(self, directory: str, name: str, size: int, content_type: str, etag: str):
        self.directory = directory
        self.name = name
        self.size = size
        self.content_type = content_type
        self.etag = etag


class StorageClient(ABC):
    """
    An abstract interface to storage client
    """
    @abstractmethod
    def get_file_stat(self, directory: str, file_name: str) -> StorageItem | None:
        """
        Returns files stats (:class:`StorageItem`)
        :param directory: Directory
        :param file_name: File name
        :return: :class:`StorageItem` or `None` if file was not found
        """
        pass

    @abstractmethod
    def load_file(self, directory: str, file_name: str) -> BytesIO | None:
        """
        Loads the given file into memory as :class:`BytesIO`
        :param directory: Directory
        :param file_name: File name
        :return: :class:`BytesIO` with loaded bytes, returns `None` if file was not found
        """
        pass

    @abstractmethod
    def put_file(self, directory: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True) -> int:
        """
        Uploads files to storage
        :param directory: Destination directory
        :param file_name: Destination file name
        :param content: Content
        :param content_type: Destination content_type
        :param reset_content: Set true to reset source content to the beginning
        :return: Upload bytes count - size of the content
        """
        pass


class S3StorageClient(StorageClient):
    _minioClient: Minio

    def __init__(self, minio: Minio):
        assert minio is not None, "Minio client is required"

        self._minioClient = minio

    def get_file_stat(self, directory: str, file_name: str) -> StorageItem | None:
        try:
            object_stat = self._minioClient.stat_object(bucket_name=directory, object_name=file_name)
            return StorageItem(directory=directory, name=file_name, size=object_stat.size,
                               content_type=object_stat.content_type, etag=object_stat.etag)
        except S3Error:
            # file was not found
            return None

    def put_file(self, directory: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True) -> int:
        assert content is not None, "Content is required"

        # read content length
        content.seek(0, os.SEEK_END)
        content_length = content.tell()

        # seek to the start to put file
        content.seek(0, os.SEEK_SET)
        self._minioClient.put_object(directory, file_name, content, content_length, content_type=content_type)
        if reset_content:
            content.seek(0, os.SEEK_SET)
        return content_length

    def load_file(self, directory: str, file_name: str) -> BytesIO | None:
        result = BytesIO()
        http_response: BaseHTTPResponse | None = None
        try:
            http_response = self._minioClient.get_object(directory, file_name)
            result = self._load_response_to_memory(http_response)
            return result
        except S3Error:
            result.close()
            return None
        except Exception as e:
            result.close()
            raise e
        finally:
            if http_response:
                http_response.close()
                http_response.release_conn()

    @staticmethod
    def _load_response_to_memory(response: BaseHTTPResponse) -> BytesIO:
        result = BytesIO()
        try:
            stream = response.stream()
            for chunk in stream:
                result.write(chunk)
            result.seek(0, os.SEEK_SET)
            return result
        finally:
            response.close()
            response.release_conn()

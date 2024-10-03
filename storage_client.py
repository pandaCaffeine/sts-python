import os
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO

from minio import Minio, S3Error
from minio.commonconfig import ENABLED
from minio.lifecycleconfig import LifecycleConfig, Rule, Transition
from urllib3 import BaseHTTPResponse


@dataclass
class StorageFileItem:
    """
    Contains file's information
    """
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
        """
        Constructor
        :param directory: Directory
        :param name: File name
        :param size: File size in bytes
        :param content_type: Content type, MIME type
        :param etag: File's Etag
        """
        self.directory = directory
        self.name = name
        self.size = size
        self.content_type = content_type
        self.etag = etag


class StorageResponse(ABC):
    @abstractmethod
    def read_to_end(self) -> Iterable[bytes]:
        pass

    @abstractmethod
    def close(self):
        pass


class StorageClient(ABC):
    """
    An abstract interface to storage client
    """

    @abstractmethod
    def get_file_stat(self, directory: str, file_name: str) -> StorageFileItem | None:
        """
        Returns files stats (:class:`StorageItem`)
        :param directory: Directory
        :param file_name: File name
        :return: :class:`StorageItem` or `None` if file was not found
        """
        pass

    @abstractmethod
    def open_stream(self, directory: str, file_name: str) -> StorageResponse:
        """
        Opens stream to read bytes
        :param directory: Directory
        :param file_name: File name
        :return: Bytes or None if file was not found
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
                 reset_content: bool = True) -> StorageFileItem:
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

    @abstractmethod
    def try_create_dir(self, directory: str) -> bool:
        """
        Tries to create directory in storage
        :param directory: Directory name
        :return: True if directory was created, False if directory already exists
        """
        pass


class _StorageResponse(StorageResponse):
    __http_response: BaseHTTPResponse

    def __init__(self, http_response: BaseHTTPResponse):
        self.__http_response = http_response

    def read_to_end(self) -> Iterable[bytes]:
        try:
            stream = self.__http_response.stream()
            for chunk in stream:
                yield chunk
        finally:
            self.close()

    def close(self):
        self.__http_response.close()
        self.__http_response.release_conn()


class S3StorageClient(StorageClient):
    _minioClient: Minio

    def __init__(self, minio: Minio):
        assert minio is not None, "Minio client is required"

        self._minioClient = minio

    def open_stream(self, directory: str, file_name: str) -> StorageResponse | None:
        response: BaseHTTPResponse | None = None
        try:
            response = self._minioClient.get_object(directory, file_name)
            return _StorageResponse(response)
        except S3Error:
            if response:
                response.close()
                response.release_conn()
            return None
        except Exception as e:
            if response:
                response.close()
                response.release_conn()
            raise e

    def try_create_dir(self, directory: str) -> bool:
        if self._minioClient.bucket_exists(directory):
            return False

        self._minioClient.make_bucket(directory)

        ttl_config = LifecycleConfig(
            [
                Rule(ENABLED, rule_id="stsTtlRule", transition=Transition(days=30))
            ]
        )
        self._minioClient.set_bucket_lifecycle(directory, ttl_config)
        return True

    def get_file_stat(self, directory: str, file_name: str) -> StorageFileItem | None:
        try:
            object_stat = self._minioClient.stat_object(bucket_name=directory, object_name=file_name)
            return StorageFileItem(directory=directory, name=file_name, size=object_stat.size,
                                   content_type=object_stat.content_type, etag=object_stat.etag)
        except S3Error:
            return None

    def put_file(self, directory: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True) -> StorageFileItem:
        assert content is not None, "Content is required"

        # read content length
        content.seek(0, os.SEEK_END)
        content_length = content.tell()

        # seek to the start to put file
        content.seek(0, os.SEEK_SET)
        result = self._minioClient.put_object(directory, file_name, content, content_length, content_type=content_type)
        if reset_content:
            content.seek(0, os.SEEK_SET)
        return StorageFileItem(directory=directory, name=result.object_name, content_type=content_type,
                               size=content_length, etag=result.etag)

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

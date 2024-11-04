import os
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO

from minio import Minio, S3Error
from minio.commonconfig import ENABLED, Filter
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from urllib3 import BaseHTTPResponse


@dataclass
class StorageFileItem:
    """
    Contains file's information
    """
    directory: str
    """ File location """
    file_name: str
    """ File name """
    size: int
    """ File size """
    content_type: str
    """ Content type """
    etag: str
    """ File's Etag """
    metadata: dict[str, str]
    """ File's metadata """

    def __init__(self, directory: str, file_name: str, size: int, content_type: str, etag: str, metadata: dict[str, str]):
        """
        Constructor
        :param directory: Directory
        :param file_name: File name
        :param size: File size in bytes
        :param content_type: Content type, MIME type
        :param etag: File's Etag
        """
        self.directory = directory
        self.file_name = file_name
        self.size = size
        self.content_type = content_type
        self.etag = etag
        self.metadata = metadata


class StorageResponse(ABC):
    @abstractmethod
    def read_to_end(self) -> Iterable[bytes]:
        pass

    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def content_length(self) -> str:
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        pass

    @property
    @abstractmethod
    def etag(self) -> str:
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
                 reset_content: bool = True, metadata: dict[str, str] | None = None) -> StorageFileItem:
        """
        Uploads files to storage
        :param directory: Destination directory
        :param file_name: Destination file name
        :param content: Content
        :param content_type: Destination content_type
        :param reset_content: Set true to reset source content to the beginning
        :param metadata: File's optional metadata
        :return: Upload bytes count - size of the content
        """
        pass

    @abstractmethod
    def try_create_dir(self, directory: str, life_time_days: int) -> bool:
        """
        Tries to create directory in storage
        :param life_time_days: How many days files in the bucket live, in days. 30 days by default
        :param directory: Directory name
        :return: True if directory was created, False if directory already exists
        """
        pass


class _StorageResponse(StorageResponse):
    __http_response: BaseHTTPResponse
    __content_length: str
    __content_type: str
    __etag: str

    def __init__(self, http_response: BaseHTTPResponse):
        self.__http_response = http_response
        self.__content_length = self.__http_response.headers['content-length']
        self.__content_type = self.__http_response.headers['content-type']
        self.__etag = self.__http_response.headers['etag']

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

    @property
    def content_length(self) -> str:
        return self.__content_length

    @property
    def content_type(self) -> str:
        return self.__content_type

    @property
    def etag(self) -> str:
        return self.__etag


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

    def try_create_dir(self, directory: str, life_time_days: int) -> bool:
        if self._minioClient.bucket_exists(directory):
            return False

        self._minioClient.make_bucket(directory)

        if life_time_days > 0:
            ttl_config = LifecycleConfig(
                [
                    Rule(ENABLED, rule_id="stsTtlRule", expiration=Expiration(days=life_time_days),
                         rule_filter=Filter(prefix=""))
                ]
            )
            self._minioClient.set_bucket_lifecycle(directory, ttl_config)
        return True

    def get_file_stat(self, directory: str, file_name: str) -> StorageFileItem | None:
        try:
            object_stat = self._minioClient.stat_object(bucket_name=directory, object_name=file_name)
            return StorageFileItem(directory=directory, file_name=file_name, size=object_stat.size,
                                   content_type=object_stat.content_type, etag=object_stat.etag,
                                   metadata=dict(object_stat.metadata))
        except S3Error:
            return None

    def put_file(self, directory: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True, metadata: dict[str, str] | None = None) -> StorageFileItem:
        assert content is not None, "Content is required"

        # read content length
        content.seek(0, os.SEEK_END)
        content_length = content.tell()

        # seek to the start to put file
        content.seek(0, os.SEEK_SET)
        result = self._minioClient.put_object(directory, file_name, content, content_length, content_type=content_type, metadata=metadata)
        if reset_content:
            content.seek(0, os.SEEK_SET)
        return StorageFileItem(directory=directory, file_name=result.object_name, content_type=content_type,
                               size=content_length, etag=result.etag, metadata=metadata)

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

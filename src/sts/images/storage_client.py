import functools
import os
import typing
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

import anyio.to_thread
from minio import Minio, S3Error
from minio.commonconfig import ENABLED, Filter
from minio.datatypes import Object
from minio.helpers import DictType, ObjectWriteResult
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from urllib3 import BaseHTTPResponse

KEY_PARENT_ETAG: str = "x-amz-meta-parent-etag"

T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class _AsyncMinio:
    _minio: Minio

    def __init__(self, minio: Minio):
        if not minio:
            raise ValueError("minio is required")

        self._minio = minio

    @staticmethod
    async def _run_async(func: typing.Callable[P, T], *args, **kwargs) -> T:
        func = functools.partial(func, *args, **kwargs)
        return await anyio.to_thread.run_sync(func)

    async def get_object(self, bucket_name: str, object_name: str) -> BaseHTTPResponse:
        return await self._run_async(self._minio.get_object, bucket_name=bucket_name, object_name=object_name)

    async def load_file(self, bucket_name: str, object_name: str) -> BytesIO:
        obj = await self.get_object(bucket_name, object_name)
        return await self._load_to_memory(obj)

    async def bucket_exists(self, bucket_name: str) -> bool:
        return await self._run_async(self._minio.bucket_exists, bucket_name=bucket_name)

    async def make_bucket(self, bucket_name: str) -> None:
        return await self._run_async(self._minio.make_bucket, bucket_name=bucket_name)

    async def set_bucket_lifecycle(self, bucket_name: str, config: LifecycleConfig) -> None:
        return await self._run_async(self._minio.set_bucket_lifecycle, bucket_name=bucket_name, config=config)

    async def stat_object(self, bucket_name: str, object_name: str) -> Object:
        return await self._run_async(self._minio.stat_object, bucket_name=bucket_name, object_name=object_name)

    async def put_object(self,
                         bucket_name: str,
                         object_name: str,
                         data: BinaryIO,
                         length: int,
                         content_type: str,
                         metadata: DictType | None) -> ObjectWriteResult:
        return await self._run_async(self._minio.put_object, bucket_name=bucket_name, object_name=object_name,
                                     data=data, length=length, content_type=content_type, metadata=metadata)

    @staticmethod
    async def _load_to_memory(response: BaseHTTPResponse) -> BytesIO:
        def sync_load() -> BytesIO:
            result: BytesIO = BytesIO()
            try:
                stream = response.stream()
                for chunk in stream:
                    result.write(chunk)
                result.seek(0, os.SEEK_SET)
            finally:
                response.close()
                response.release_conn()
            return result

        return await anyio.to_thread.run_sync(sync_load)



@dataclass(frozen=True, slots=True)
class StorageFileItem:
    """ Contains file's information """
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
    async def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        """
        Returns files stats (:class:`StorageItem`)
        :param bucket: File's bucket
        :param file_name: File name
        :return: :class:`StorageItem` or `None` if file was not found
        """
        pass

    @abstractmethod
    async def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        """
        Opens stream to read bytes
        :param bucket: File's bucket
        :param file_name: File name
        :return: Bytes or None if file was not found
        """
        pass

    @abstractmethod
    async def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        """
        Loads the given file into memory as :class:`BytesIO`
        :param bucket: File's bucket
        :param file_name: File name
        :return: :class:`BytesIO` with loaded bytes, returns `None` if file was not found
        """
        pass

    @abstractmethod
    async def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
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
    async def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        """
        Tries to create bucket in storage
        :param life_time_days: How many days files in the bucket live, in days
        :param bucket: Bucket name
        :return: True if bucket was created, False if bucket already exists
        """
        pass


class _StorageResponse(StorageResponse):
    _http_response: BaseHTTPResponse | None
    _content_length: str
    _content_type: str
    _etag: str
    __slots__ = ['_content_length', '_http_response', '_content_type', '_etag']

    def __init__(self, http_response: BaseHTTPResponse):
        assert http_response, "http_response is required"

        self._http_response = http_response
        self._content_length = self._http_response.headers['content-length']
        self._content_type = self._http_response.headers['content-type']
        self._etag = self._http_response.headers['etag']
        if self._etag:
            self._etag = self._etag.replace('"', '')

    def __enter__(self) -> Iterable[bytes]:
        assert self._http_response, "error when access http_response"
        return self._http_response.stream()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def read_to_end(self) -> Iterable[bytes]:
        with self as stream:
            yield from stream

    def close(self):
        if not self._http_response:
            return

        http_response = self._http_response
        self._http_response = None
        http_response.close()
        http_response.release_conn()

    @property
    def content_length(self) -> str:
        return self._content_length

    @property
    def content_type(self) -> str:
        return self._content_type

    @property
    def etag(self) -> str:
        return self._etag


class S3StorageClient(StorageClient):
    _minio_client: _AsyncMinio

    def __init__(self, minio: Minio):
        assert minio is not None, "Minio client is required"

        self._minio_client = _AsyncMinio(minio)

    async def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        response: BaseHTTPResponse | None = None
        try:
            response = await self._minio_client.get_object(bucket, file_name)
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

    async def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        bucket_exists = await self._minio_client.bucket_exists(bucket)
        if bucket_exists:
            return False

        await self._minio_client.make_bucket(bucket)
        if life_time_days > 0:
            ttl_config = LifecycleConfig(
                [
                    Rule(ENABLED, rule_id="stsTtlRule", expiration=Expiration(days=life_time_days),
                         rule_filter=Filter(prefix=""))
                ]
            )
            await self._minio_client.set_bucket_lifecycle(bucket, ttl_config)
        return True

    async def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        try:
            object_stat = await self._minio_client.stat_object(bucket, file_name)
            if not object_stat:
                return None

            parent_etag = object_stat.metadata.get(KEY_PARENT_ETAG, None) if object_stat.metadata else None
            return StorageFileItem(bucket=bucket, file_name=file_name, size=object_stat.size or 0,
                                   content_type=object_stat.content_type or "", etag=object_stat.etag or "",
                                   parent_etag=parent_etag)
        except S3Error:
            return None

    async def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
                       reset_content: bool = True, parent_etag: str | None = None) -> StorageFileItem:
        assert content is not None, "Content is required"

        # read content length
        content.seek(0, os.SEEK_END)
        content_length = content.tell()

        # seek to the start to put file
        content.seek(0, os.SEEK_SET)

        metadata: DictType | None = None
        if parent_etag:
            metadata = {KEY_PARENT_ETAG: parent_etag}

        result = await self._minio_client.put_object(bucket, file_name, content, content_length, content_type, metadata)
        if reset_content:
            content.seek(0, os.SEEK_SET)
        return StorageFileItem(bucket=bucket, file_name=result.object_name, content_type=content_type,
                               size=content_length, etag=result.etag or "", parent_etag=parent_etag)

    async def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        result = BytesIO()
        http_response: BaseHTTPResponse | None = None
        try:
            result = await self._minio_client.load_file(bucket, file_name)
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

import os
import shutil
from collections.abc import Iterable
from io import BytesIO

from minio import Minio, S3Error
from minio.commonconfig import ENABLED, Filter
from minio.helpers import DictType
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from urllib3 import BaseHTTPResponse

from sts.file_storage.client import FileStorageClient
from sts.models.file_storage import StorageFileItem, StorageResponse

KEY_PARENT_ETAG: str = "x-amz-meta-parent-etag"


class _MinioStorageResponse(StorageResponse):
    _http_response: BaseHTTPResponse | None = None
    _content_length: int
    _content_type: str
    _etag: str

    def __init__(self, http_response: BaseHTTPResponse):
        if not http_response:
            raise ValueError("http_response is required")

        if not http_response.headers:
            raise ValueError("http_response headers is required")

        self._http_response = http_response
        self._content_length = int(self._http_response.headers.get('content-length') or "")
        self._content_type = self._http_response.headers['content-type'] or ""
        self._etag = (self._http_response.headers['etag'] or "").replace('"', '')

    def __enter__(self) -> Iterable[bytes]:
        assert self._http_response, "error when access http_response"
        return self._http_response.stream()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
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
    def content_length(self) -> int:
        return self._content_length

    @property
    def content_type(self) -> str:
        return self._content_type

    @property
    def etag(self) -> str:
        return self._etag


class MinioFileStorageClient(FileStorageClient):
    _minio_client: Minio

    def __init__(self, minio: Minio):
        if not minio:
            raise ValueError("minio must be provided")
        self._minio_client = minio

    # --- Reading ---

    def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        response: BaseHTTPResponse | None = None
        try:
            response = self._minio_client.get_object(bucket, file_name)
            return _MinioStorageResponse(response)
        except S3Error:
            return None
        except Exception:
            if response:
                response.close()
                response.release_conn()
            raise

    def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        try:
            stat = self._minio_client.stat_object(bucket, file_name)
            meta = stat.metadata or {}

            return StorageFileItem(
                bucket=bucket,
                file_name=file_name,
                size=stat.size or 0,
                content_type=stat.content_type or "",
                etag=stat.etag or "",
                parent_etag=meta.get(KEY_PARENT_ETAG),
            )

        except S3Error:
            return None

    def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        response: BaseHTTPResponse | None = None
        try:
            response = self._minio_client.get_object(bucket, file_name)
            return self._load_response_to_memory(response)
        except S3Error:
            return None
        except Exception:
            if response:
                response.close()
                response.release_conn()
            raise

    # --- Writing ---

    def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True, parent_etag: str | None = None) -> StorageFileItem:
        if not content:
            raise ValueError("content is required")

        content.seek(0, os.SEEK_END)
        content_length = content.tell()
        # seek to the start to put file
        content.seek(0, os.SEEK_SET)

        metadata: DictType | None = {KEY_PARENT_ETAG: parent_etag} if parent_etag else None
        result = self._minio_client.put_object(
            bucket_name=bucket,
            object_name=file_name,
            data=content,
            length=content_length,
            content_type=content_type,
            metadata=metadata,
        )
        if reset_content:
            content.seek(0, os.SEEK_SET)

        return StorageFileItem(
            bucket=bucket,
            file_name=result.object_name,
            content_type=content_type,
            size=content_length,
            etag=result.etag or "",
            parent_etag=parent_etag,
        )

    # --- Bucket management --

    def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        if self._minio_client.bucket_exists(bucket):
            return False

        self._minio_client.make_bucket(bucket)

        if life_time_days > 0:
            ttl_config = LifecycleConfig([
                Rule(ENABLED,
                     rule_id="stsTtlRule",
                     expiration=Expiration(days=life_time_days),
                     rule_filter=Filter(prefix="")
                     )
            ])
            self._minio_client.set_bucket_lifecycle(bucket, ttl_config)

        return True

    # --- Helpers ---

    @staticmethod
    def _load_response_to_memory(response: BaseHTTPResponse) -> BytesIO:
        buf = BytesIO()
        try:
            shutil.copyfileobj(response, buf)
            buf.seek(0, os.SEEK_END)
        finally:
            response.close()
            response.release_conn()
        return buf

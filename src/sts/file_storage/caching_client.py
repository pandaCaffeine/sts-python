"""File storage client decorator caching file stats for a short time."""

import threading
import time
from collections import OrderedDict
from io import BytesIO

from sts.file_storage.client import FileStorageClient
from sts.models.file_storage import StorageFileItem, StorageResponse

_DEFAULT_TTL_SECONDS = 5.0
_DEFAULT_MAX_ENTRIES = 10_000


class CachingFileStorageClient(FileStorageClient):
    """
    Caches positive :meth:`get_file_stat` results for a short TTL.

    Cuts repeated stat round-trips to the storage on the hot request path.
    Only found files are cached: a missed file is always delegated to the
    inner client, so freshly uploaded sources stay immediately visible.
    Any :meth:`put_file` invalidates the cached entry for the written object.
    The cache is bounded (LRU) and thread-safe.
    """

    def __init__(self, inner: FileStorageClient, ttl_seconds: float = _DEFAULT_TTL_SECONDS,
                 max_entries: int = _DEFAULT_MAX_ENTRIES):
        if not inner:
            raise ValueError("inner client is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")

        self._inner = inner
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._cache: OrderedDict[tuple[str, str], tuple[float, StorageFileItem]] = OrderedDict()
        self._cache_lock = threading.Lock()

    # --- Reading ---

    def get_file_stat(self, bucket: str, file_name: str) -> StorageFileItem | None:
        key = (bucket, file_name)

        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is not None:
                expires_at, item = entry
                if time.monotonic() < expires_at:
                    self._cache.move_to_end(key)
                    return item
                self._cache.pop(key, None)

        stat = self._inner.get_file_stat(bucket, file_name)
        if stat is not None:
            with self._cache_lock:
                self._cache[key] = (time.monotonic() + self._ttl_seconds, stat)
                self._cache.move_to_end(key)
                while len(self._cache) > self._max_entries:
                    self._cache.popitem(last=False)

        return stat

    def open_stream(self, bucket: str, file_name: str) -> StorageResponse | None:
        return self._inner.open_stream(bucket, file_name)

    def load_file(self, bucket: str, file_name: str) -> BytesIO | None:
        return self._inner.load_file(bucket, file_name)

    # --- Writing ---

    def put_file(self, bucket: str, file_name: str, content: BytesIO, content_type: str,
                 reset_content: bool = True, parent_etag: str | None = None) -> StorageFileItem:
        result = self._inner.put_file(bucket, file_name, content, content_type,
                                      reset_content=reset_content, parent_etag=parent_etag)
        with self._cache_lock:
            self._cache.pop((bucket, file_name), None)
        return result

    # --- Bucket management ---

    def try_create_bucket(self, bucket: str, life_time_days: int) -> bool:
        return self._inner.try_create_bucket(bucket, life_time_days)

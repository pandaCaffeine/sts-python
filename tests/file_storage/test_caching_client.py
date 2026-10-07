import time
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from sts.file_storage.caching_client import CachingFileStorageClient
from sts.models.file_storage import StorageFileItem


def make_item(bucket="images", name="icon.png", etag="aaa") -> StorageFileItem:
    return StorageFileItem(bucket=bucket, file_name=name, size=1,
                           content_type="image/png", etag=etag)


def make_inner() -> MagicMock:
    return MagicMock(spec=["get_file_stat", "open_stream", "load_file",
                           "put_file", "try_create_bucket"])


def test_get_file_stat_cached_within_ttl():
    inner = make_inner()
    inner.get_file_stat.return_value = make_item()
    client = CachingFileStorageClient(inner, ttl_seconds=5)

    first = client.get_file_stat("images", "icon.png")
    second = client.get_file_stat("images", "icon.png")

    assert first is second
    inner.get_file_stat.assert_called_once_with("images", "icon.png")


def test_get_file_stat_refetches_after_ttl():
    inner = make_inner()
    inner.get_file_stat.return_value = make_item()
    client = CachingFileStorageClient(inner, ttl_seconds=0.05)

    client.get_file_stat("images", "icon.png")
    time.sleep(0.08)
    client.get_file_stat("images", "icon.png")

    assert inner.get_file_stat.call_count == 2


def test_negative_result_is_not_cached():
    inner = make_inner()
    inner.get_file_stat.return_value = None
    client = CachingFileStorageClient(inner)

    assert client.get_file_stat("images", "missing.png") is None
    assert client.get_file_stat("images", "missing.png") is None

    assert inner.get_file_stat.call_count == 2


def test_put_file_invalidates_cache():
    inner = make_inner()
    item = make_item()
    inner.get_file_stat.return_value = item
    inner.put_file.return_value = item
    client = CachingFileStorageClient(inner)

    client.get_file_stat("images", "icon.png")
    client.put_file("images", "icon.png", BytesIO(b"x"), "image/png")
    client.get_file_stat("images", "icon.png")

    assert inner.get_file_stat.call_count == 2


def test_different_keys_cached_separately():
    inner = make_inner()
    inner.get_file_stat.side_effect = lambda bucket, name: make_item(name=name)
    client = CachingFileStorageClient(inner)

    client.get_file_stat("images", "a.png")
    client.get_file_stat("images", "b.png")
    client.get_file_stat("images", "a.png")

    assert inner.get_file_stat.call_count == 2


def test_max_entries_evicts_oldest():
    inner = make_inner()
    inner.get_file_stat.side_effect = lambda bucket, name: make_item(name=name)
    client = CachingFileStorageClient(inner, ttl_seconds=5, max_entries=1)

    client.get_file_stat("images", "a.png")
    client.get_file_stat("images", "b.png")  # evicts a.png
    client.get_file_stat("images", "a.png")  # refetched

    assert inner.get_file_stat.call_count == 3


def test_passthrough_methods_delegate_to_inner():
    inner = make_inner()
    stream = MagicMock()
    buf = BytesIO(b"x")
    inner.open_stream.return_value = stream
    inner.load_file.return_value = buf
    inner.try_create_bucket.return_value = True
    client = CachingFileStorageClient(inner)

    assert client.open_stream("images", "a.png") is stream
    assert client.load_file("images", "a.png") is buf
    assert client.try_create_bucket("images", 30) is True


def test_constructor_validation():
    with pytest.raises(ValueError):
        CachingFileStorageClient(None)  # type: ignore[arg-type]

    inner = make_inner()
    with pytest.raises(ValueError):
        CachingFileStorageClient(inner, ttl_seconds=0)
    with pytest.raises(ValueError):
        CachingFileStorageClient(inner, max_entries=0)

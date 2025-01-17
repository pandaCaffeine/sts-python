import os
import unittest.mock
from io import BytesIO
from unittest.mock import create_autospec, Mock

import minio.datatypes
import pytest
from minio import Minio, S3Error
from minio.helpers import ObjectWriteResult
from urllib3 import HTTPResponse, HTTPHeaderDict

from sts.images.storage_client import S3StorageClient

_expected_content_length = '1024'
_expected_content_type = 'image/png'
_expected_etag = '53e2a123b39d45339b7d6f14b99292b8'

_fake_response = HTTPResponse(body='', headers={
    'content-length': _expected_content_length,
    'content-type': _expected_content_type,
    'etag': f'"{_expected_etag}"'
}, status=200, version=1, version_string='1', reason=None,
                              decode_content=False, request_url='http://minio/images/icon.png')


def __read_file(file_name: str) -> BytesIO:
    with open(file_name, "rb") as file_data:
        return BytesIO(file_data.read())


def test_open_stream_successful():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.return_value = _fake_response

    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.open_stream('images', 'icon.png')

    # assert
    assert result
    assert result.etag == _expected_etag
    assert result.content_type == _expected_content_type
    assert result.content_length == _expected_content_length


def test_open_stream_returns_none_when_s3_error():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.side_effect = S3Error('unit-test', 'unit test error', None, None, None,
                                                response=_fake_response)

    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.open_stream('images', 'icon.png')

    # assert
    assert not result


def test_open_stream_returns_none_when_exception():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.side_effect = ValueError('unit test error')

    storage_client = S3StorageClient(minio_mock)

    # act & assert
    with pytest.raises(ValueError):
        storage_client.open_stream('images', 'icon.png')


def test_try_create_dir_does_nothing_if_bucket_exits():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.bucket_exists.return_value = True
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.try_create_dir('test', 30)

    # assert
    assert not result


def test_try_create_dir_successful():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.bucket_exists.return_value = False
    minio_mock.make_bucket = Mock(return_value=None)
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.try_create_dir('test', 30)

    # assert
    assert result
    minio_mock.make_bucket.assert_called_with('test')
    minio_mock.set_bucket_lifecycle.assert_called_once_with('test', unittest.mock.ANY)


def test_get_file_stat_returns_none():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.stat_object.return_value = None
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.get_file_stat('images', 'icon.png')

    # assert
    assert not result


def test_get_file_stat_successful():
    # arrange
    fake_minio_object = minio.datatypes.Object('images', 'icon.png', etag=_expected_etag, size=1024,
                                               content_type=_expected_content_type)
    minio_mock = create_autospec(Minio)
    minio_mock.stat_object.return_value = fake_minio_object
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.get_file_stat('images', 'icon.png')

    # assert
    assert result


def test_get_file_stat_returns_none_when_s3_error():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.stat_object.side_effect = S3Error('unit-test', 'unit test error', None, None, None,
                                                 response=_fake_response)
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.get_file_stat('images', 'icon.png')

    # asser
    assert result is None


@pytest.mark.parametrize('expected_parent_etag', [_expected_etag, None])
def test_put_file_successful(expected_parent_etag: str | None):
    # arrange
    expected_bucket_name = 'images-small'
    expected_object_name = 'icon.png'

    minio_mock = create_autospec(Minio)
    minio_mock.put_object.return_value = ObjectWriteResult(expected_bucket_name, expected_object_name, None,
                                                           etag=_expected_etag, http_headers=HTTPHeaderDict())
    storage_client = S3StorageClient(minio_mock)
    file_memory = __read_file('./test.png')
    file_memory.seek(0, os.SEEK_END)
    expected_size = file_memory.tell()
    file_memory.seek(0, os.SEEK_SET)

    # act
    result = storage_client.put_file(expected_bucket_name, expected_object_name, file_memory, _expected_content_type,
                                     parent_etag=expected_parent_etag)

    # assert
    assert result
    assert result.size == expected_size
    assert result.directory == expected_bucket_name
    assert result.file_name == expected_object_name
    assert result.content_type == _expected_content_type
    assert result.etag == _expected_etag
    assert result.parent_etag == expected_parent_etag
    assert file_memory.tell() == 0

def test_load_file_returns_none_when_s3_error():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.side_effect = S3Error('unit-test', 'unit test error', None, None, None,
                                                response=_fake_response)
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.load_file('images', 'icon.png')

    # assert
    assert not result

def test_load_file_fails_when_error():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.side_effect = ValueError('unit test error')
    storage_client = S3StorageClient(minio_mock)

    # act & assert
    with pytest.raises(ValueError):
        storage_client.load_file('images', 'icon.png')

def test_load_file_successful():
    # arrange
    fake_file = __read_file('./test.png')
    expected_size = fake_file.tell()
    fake_file.seek(0, os.SEEK_SET)

    minio_mock = create_autospec(Minio)
    minio_mock.get_object.return_value = HTTPResponse(fake_file, None, 200, 1, 'HTTP/1.0',
                                                      None)
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.load_file('images', 'icon.png')

    # assert
    assert result
    result.seek(0, os.SEEK_END)
    assert result.tell() == expected_size


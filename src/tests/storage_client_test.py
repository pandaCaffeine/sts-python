import unittest.mock
from unittest.mock import create_autospec, Mock

import minio.datatypes
import pytest
from minio import Minio, S3Error
from urllib3 import HTTPResponse

from sts.images.storage_client import S3StorageClient

expected_content_length = '1024'
expected_content_type = 'image/png'
expected_etag = '53e2a123b39d45339b7d6f14b99292b8'

fake_response = HTTPResponse(body='', headers={
    'content-length': expected_content_length,
    'content-type': expected_content_type,
    'etag': f'"{expected_etag}"'
}, status=200, version=1, version_string='1', reason=None,
                             decode_content=False, request_url='http://minio/images/icon.png')


def test_open_stream_successful():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.return_value = fake_response

    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.open_stream('images', 'icon.png')

    # assert
    assert result
    assert result.etag == expected_etag
    assert result.content_type == expected_content_type
    assert result.content_length == expected_content_length


def test_open_stream_returns_none_when_s3_error():
    # arrange
    minio_mock = create_autospec(Minio)
    minio_mock.get_object.side_effect = S3Error('unit-test', 'unit test error', None, None, None,
                                                response=fake_response)

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
    fake_minio_object = minio.datatypes.Object('images', 'icon.png', etag=expected_etag, size=1024,
                                               content_type=expected_content_type)
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
                                                response=fake_response)
    storage_client = S3StorageClient(minio_mock)

    # act
    result = storage_client.get_file_stat('images', 'icon.png')

    # asser
    assert result is None



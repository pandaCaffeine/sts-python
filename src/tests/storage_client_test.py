from unittest.mock import create_autospec

import pytest
from minio import Minio, S3Error
from urllib3 import HTTPResponse

from sts.images.storage_client import S3StorageClient

expected_content_length = '1024'
expected_content_type = 'image/png'
expected_etag = '53e2a123b39d45339b7d6f14b99292b8'

fake_response = HTTPResponse(body="", headers={
    'content-length': expected_content_length,
    'content-type': expected_content_type,
    'etag': f'"{expected_etag}"'
}, status=200, version=1, version_string="1", reason=None,
                             decode_content=False, request_url="http://minio/images/icon.png")


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
    minio_mock.get_object.side_effect = S3Error("unit-test", "unit test error", None, None, None,
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

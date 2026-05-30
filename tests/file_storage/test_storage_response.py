from urllib3 import HTTPResponse

from sts.file_storage.minio_client import _MinioStorageResponse

_expected_content_length = '1024'
_expected_content_type = 'image/png'
_expected_etag = '53e2a123b39d45339b7d6f14b99292b8'

_fake_response = HTTPResponse(body='', headers={'content-length': _expected_content_length,
                                                'content-type': _expected_content_type,
                                                'etag': f'"{_expected_etag}"'
                                                }, status=200, version=1, version_string='1', reason=None,
                              decode_content=False, request_url='http://minio/images/icon.png')


def test_storage_response_init_successful():
    # act
    storage_response = _MinioStorageResponse(_fake_response)

    # assert
    assert storage_response.etag == _expected_etag
    assert storage_response.content_type == _expected_content_type
    assert storage_response.content_length == int(_expected_content_length)

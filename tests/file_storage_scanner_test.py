from unittest.mock import create_autospec

from sts.config import BucketSettings, ImageSize, BucketsMap
from sts.file_storage.minio_scanner import MinioFileStorageScanner
from sts.models.enums import ScanStatus
from sts.file_storage.client import FileStorageClient
from sts.models.file_storage import StorageFileItem

_buckets = {
    'images': BucketSettings(source_bucket='images', size=ImageSize()),
    'thumbnail-small': BucketSettings(size=ImageSize(w=100, h=100), source_bucket='images', alias='small',
                                      life_time_days=30),
    'thumbnail-medium': BucketSettings(size=ImageSize(w=300, h=300), source_bucket='images', alias='medium',
                                       life_time_days=30)}
_buckets_map = BucketsMap(source_bucket="images", buckets=_buckets,
                          alias_map={'small': 'thumbnail-small', 'medium': 'thumbnail-medium'},
                          all_source_buckets={'images'})
_default_storage_client_mock = create_autospec(FileStorageClient)
_default_storage_client_mock.get_file_stat.return_value = StorageFileItem('unit',
                                                                          'test.png',
                                                                          1024,
                                                                          'image/png',
                                                                          "abcdef123", None)


def test_file_storage_bucket_not_found():
    scanner = MinioFileStorageScanner(_default_storage_client_mock, _buckets_map)
    result = scanner.scan_file('images2', 'icon.png')
    assert result.status == ScanStatus.BUCKET_NOT_FOUND


def test_file_storage_source_file_not_found():
    storage_client_mock = create_autospec(FileStorageClient)
    storage_client_mock.get_file_stat.return_value = None

    scanner = MinioFileStorageScanner(storage_client_mock, _buckets_map)
    result = scanner.scan_file('images', 'test.png')
    assert result.status == ScanStatus.SOURCE_FILE_NOT_FOUND


def test_file_storage_use_source_file():
    scanner = MinioFileStorageScanner(_default_storage_client_mock, _buckets_map)
    result = scanner.scan_file('images', 'icon.png')
    assert result.status == ScanStatus.USE_SOURCE_FILE


def test_file_storage_file_found():
    def side_effect(*args):
        if args[1] == 'icon.png' and args[0] == 'images':
            return StorageFileItem(file_name='icon.png', etag='valid', bucket='images', size=1, parent_etag=None,
                                   content_type='image/png')
        else:
            return StorageFileItem(file_name='icon.png', etag='valid-small', bucket='thumbnail-small', size=1,
                                   parent_etag='valid',
                                   content_type='image/png')

    storage_client_mock = create_autospec(FileStorageClient)
    storage_client_mock.get_file_stat.side_effect = side_effect

    scanner = MinioFileStorageScanner(storage_client_mock, _buckets_map)
    result = scanner.scan_file('thumbnail-small', 'icon.png')
    assert result.status == ScanStatus.FILE_FOUND


def test_file_storage_create_new():
    def side_effect(*args):
        if args[1] == 'icon.png' and args[0] == 'images':
            return StorageFileItem(file_name='icon.png', etag='valid', bucket='images', size=1, parent_etag=None,
                                   content_type='image/png')
        else:
            return StorageFileItem(file_name='icon.png', etag='valid-small', bucket='thumbnail-small', size=1,
                                   parent_etag='invalid',
                                   content_type='image/png')

    storage_client_mock = create_autospec(FileStorageClient)
    storage_client_mock.get_file_stat.side_effect = side_effect

    scanner = MinioFileStorageScanner(storage_client_mock, _buckets_map)
    result = scanner.scan_file('thumbnail-small', 'icon.png')
    assert result.status == ScanStatus.CREATE_NEW

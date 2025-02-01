from unittest.mock import create_autospec

from sts.config import BucketSettings, ImageSize, BucketsMap
from sts.images.file_storage_scanner import FileStorageScannerImpl, ScanStatus
from sts.images.storage_client import StorageClient, StorageFileItem

_buckets = {
    'images': BucketSettings(source_bucket='images', size=ImageSize()),
    'thumbnail-small': BucketSettings(size=ImageSize(100, 100), source_bucket='images', alias='small',
                                      life_time_days=30),
    'thumbnail-medium': BucketSettings(size=ImageSize(300, 300), source_bucket='images', alias='medium',
                                       life_time_days=30)}
_buckets_map = BucketsMap(source_bucket="images", buckets=_buckets,
                          alias_map={'small': 'thumbnail-small', 'medium': 'thumbnail-medium'},
                          all_source_buckets={'images'})
_default_storage_client_mock = create_autospec(StorageClient)


def test_file_storage_bucket_not_found():
    scanner = FileStorageScannerImpl(_default_storage_client_mock, _buckets_map)
    result = scanner.scan_file('images2', 'icon.png')
    assert result.status == ScanStatus.BUCKET_NOT_FOUND


def test_file_storage_source_file_not_found():
    storage_client_mock = create_autospec(StorageClient)
    storage_client_mock.get_file_stat.return_value = None

    scanner = FileStorageScannerImpl(storage_client_mock, _buckets_map)
    result = scanner.scan_file('images', 'test.png')
    assert result.status == ScanStatus.SOURCE_FILE_NOT_FOUND


def test_file_storage_use_source_file():
    scanner = FileStorageScannerImpl(_default_storage_client_mock, _buckets_map)
    result = scanner.scan_file('images', 'icon.png')
    assert result.status == ScanStatus.USE_SOURCE_FILE


def test_file_storage_file_found():
    def side_effect(*args, **kwargs):
        if args[1] == 'icon.png' and args[0] == 'images':
            return StorageFileItem(file_name='icon.png', etag='valid', bucket='images', size=1, parent_etag=None,
                                   content_type='image/png')
        else:
            return StorageFileItem(file_name='icon.png', etag='valid-small', bucket='thumbnail-small', size=1,
                                   parent_etag='valid',
                                   content_type='image/png')

    storage_client_mock = create_autospec(StorageClient)
    storage_client_mock.get_file_stat.side_effect = side_effect

    scanner = FileStorageScannerImpl(storage_client_mock, _buckets_map)
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

    storage_client_mock = create_autospec(StorageClient)
    storage_client_mock.get_file_stat.side_effect = side_effect

    scanner = FileStorageScannerImpl(storage_client_mock, _buckets_map)
    result = scanner.scan_file('thumbnail-small', 'icon.png')
    assert result.status == ScanStatus.CREATE_NEW

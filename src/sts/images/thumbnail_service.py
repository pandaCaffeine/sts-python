from logging import Logger

from starlette import status
from starlette.responses import Response, StreamingResponse, JSONResponse

from sts.config import BucketSettings
from sts.images.file_storage_scanner import FileStorageScanner, ScanStatus
from sts.images.image_processor import resize_image
from sts.images.storage_client import StorageClient, StorageFileItem

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"

NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                content={"detail": "File not found"})


class ThumbnailService:
    _storage_client: StorageClient
    _logger: Logger
    _file_storage_scanner: FileStorageScanner

    def __init__(self, storage_client: StorageClient, file_storage_scanner: FileStorageScanner,
                 logger: Logger):
        assert storage_client is not None, "storage_client is required"
        assert logger is not None, "logger is required"
        assert file_storage_scanner, "file_storage_scanner is required"

        self._storage_client = storage_client
        self._logger = logger
        self._file_storage_scanner = file_storage_scanner

    def get_thumbnail(self, bucket: str, file_name: str, etag: str | None) -> Response:
        scan_result = self._file_storage_scanner.scan_file(bucket, file_name)
        result: Response

        if scan_result.status == ScanStatus.BUCKET_NOT_FOUND:
            self._logger.debug(f"Bucket {bucket} is not configured")
            result = NOT_FOUND_RESPONSE
        elif scan_result.status == ScanStatus.SOURCE_FILE_NOT_FOUND:
            self._logger.debug("Source file was not found")
            result = NOT_FOUND_RESPONSE
        elif scan_result.status == ScanStatus.USE_SOURCE_FILE:
            assert scan_result.source_file_stat, "scan_result doesn't have source_file_stat"
            result = self._get_file_response(scan_result.source_file_stat, etag)
        elif scan_result.status == ScanStatus.FILE_FOUND:
            self._logger.debug("Found thumbnail file")
            assert scan_result.file_stat, "scan_result doesn't have file_stat"
            result = self._get_file_response(scan_result.file_stat, etag)
        else:
            assert scan_result.source_file_stat, "scan_result doesn't have source_file_stat"
            assert scan_result.bucket_settings, "scan_result doesn't have bucket_settings"
            result = self._create_thumbnail_and_upload(scan_result.source_file_stat,
                                                       scan_result.bucket_settings,
                                                       bucket)

        return result

    def get_thumbnail_by_alias(self, source_bucket: str, file_name: str, alias: str, etag: str | None) -> Response:
        result: Response
        bucket = self._file_storage_scanner.find_bucket_by_alias(source_bucket, alias)
        if bucket:
            result = self.get_thumbnail(bucket, file_name, etag)
        else:
            self._logger.debug(f"Source bucket {source_bucket} was not found, return 404")
            result = NOT_FOUND_RESPONSE

        return result

    def _create_thumbnail_and_upload(self, source_file_stat: StorageFileItem,
                                     bucket_settings: BucketSettings, bucket: str) -> Response:
        image_data = self._storage_client.load_file(source_file_stat.bucket, source_file_stat.file_name)
        if not image_data:
            self._logger.debug("Source file was not found")
            return NOT_FOUND_RESPONSE

        self._logger.debug("Source file was loaded into memory")
        thumbnail = resize_image(image_data,
                                 bucket_settings.size.w, bucket_settings.size.h,
                                 bucket_settings.format, bucket_settings.format_args)
        if thumbnail.error or not thumbnail.data:
            self._logger.warning(f"Failed to create thumbnail: {thumbnail.error}")
            return NOT_FOUND_RESPONSE

        self._logger.debug("Thumbnail file was created")
        put_result = self._storage_client.put_file(bucket, source_file_stat.file_name, thumbnail.data,
                                                   content_type=thumbnail.content_type,
                                                   parent_etag=source_file_stat.etag)
        self._logger.debug("Thumbnail was uploaded to storage")

        headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
        return StreamingResponse(thumbnail.data, media_type=thumbnail.content_type,
                                 headers=headers)

    def _get_file_response(self, file_storage_item: StorageFileItem, etag: str | None) -> Response:
        if etag and file_storage_item.etag == etag:
            self._logger.debug(f"Requested file has the same etag: {etag}")
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        self._logger.debug("Etag is different, return file from bucket")
        object_stream = self._storage_client.open_stream(file_storage_item.bucket, file_storage_item.file_name)
        if not object_stream:
            return NOT_FOUND_RESPONSE

        headers = {HEADER_ETAG: object_stream.etag, HEADER_LEN: object_stream.content_length}
        return StreamingResponse(object_stream.read_to_end(), media_type=object_stream.content_type, headers=headers)

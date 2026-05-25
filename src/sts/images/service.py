from starlette.background import BackgroundTask

from sts.models.file_storage import ScanResultFileFound, ScanResultCreateNew
from fastapi import status
from fastapi.responses import Response, StreamingResponse, JSONResponse

from sts.config import BucketSettings
from sts.file_storage.client import FileStorageClient
from sts.file_storage.scanner import FileStorageScanner
from sts.images.processor import resize_image
from sts.logs import ILogger
from sts.models.file_storage import StorageFileItem, ScanResultNotFound, ScanResultUseSourceFile

_HEADER_ETAG = "Etag"
_HEADER_LEN = "Content-Length"

_NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(
    status_code=status.HTTP_404_NOT_FOUND,
    content={"detail": "File not found"},
)


class ThumbnailService:
    """Handles thumbnail retrieval, creation, and storage responses."""

    def __init__(
            self,
            storage_client: FileStorageClient,
            file_storage_scanner: FileStorageScanner,
            logger: ILogger
    ) -> None:
        if not storage_client:
            raise ValueError("storage_client is required")
        if not logger:
            raise ValueError("logger is required")
        if not file_storage_scanner:
            raise ValueError("file_storage_scanner is required")

        self._storage_client = storage_client
        self._file_storage_scanner = file_storage_scanner
        self._logger = logger

    def get_thumbnail(self, bucket: str, file_name: str, etag: str | None) -> Response:
        """Retrieves an existing thumbnail, the source file, or creates a new thumbnail."""
        scan_result = self._file_storage_scanner.scan_file(bucket, file_name)

        match scan_result:
            case ScanResultNotFound():
                self._logger.debug(f"File not found in {bucket}/{file_name}: {scan_result.reason}")
                return _NOT_FOUND_RESPONSE

            case ScanResultUseSourceFile():
                return self._get_file_response(scan_result.source_file_stat, etag)

            case ScanResultFileFound():
                return self._get_file_response(scan_result.file_stat, etag)

            case ScanResultCreateNew():
                return self._create_thumbnail_and_upload(
                    source_file_stat=scan_result.source_file_stat,
                    bucket_settings=scan_result.bucket_settings,
                    bucket=bucket,
                )

            case _:
                self._logger.warning(f"Unhandled scan status: {scan_result.status}")
                return _NOT_FOUND_RESPONSE

    def get_thumbnail_by_alias(
            self,
            source_bucket: str,
            file_name: str,
            alias: str,
            etag: str | None) -> Response:
        """Resolves bucket by alias and retrieves thumbnail."""
        bucket = self._file_storage_scanner.find_bucket_by_alias(source_bucket, alias)
        if not bucket:
            self._logger.debug(f"Source bucket {source_bucket} was not found, return 404")
            return _NOT_FOUND_RESPONSE

        return self.get_thumbnail(bucket, file_name, etag)

    def _create_thumbnail_and_upload(
            self,
            source_file_stat: StorageFileItem,
            bucket_settings: BucketSettings,
            bucket: str) -> Response:
        """Loads source, resizes it, uploads it to storage, and returns a streaming response."""
        image_data = self._storage_client.load_file(bucket=source_file_stat.bucket,
                                                    file_name=source_file_stat.file_name)
        if not image_data:
            self._logger.debug("Source file was not found")
            return _NOT_FOUND_RESPONSE

        thumbnail = resize_image(image_data,
                                 bucket_settings.size.w, bucket_settings.size.h,
                                 bucket_settings.format, bucket_settings.format_args)
        if thumbnail.error or not thumbnail.data:
            self._logger.warning(f"Failed to create thumbnail: {thumbnail.error}")
            return _NOT_FOUND_RESPONSE

        put_result = self._storage_client.put_file(
            bucket=bucket,
            file_name=source_file_stat.file_name,
            content=thumbnail.data,
            content_type=thumbnail.content_type,
            parent_etag=source_file_stat.etag,
        )
        self._logger.debug("Thumbnail was uploaded to storage")

        return StreamingResponse(
            thumbnail.data,
            media_type=thumbnail.content_type,
            headers={_HEADER_ETAG: put_result.etag, _HEADER_LEN: str(put_result.size)},
        )

    def _get_file_response(self, file_storage_item: StorageFileItem, etag: str | None) -> Response:
        """Streams an existing file from storage, respecting Etag/304 caching."""
        if etag and file_storage_item.etag == etag:
            headers = {_HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        stream = self._storage_client.open_stream(file_storage_item.bucket, file_storage_item.file_name)
        if not stream:
            return _NOT_FOUND_RESPONSE

        background_task = BackgroundTask(stream.close)
        headers = {_HEADER_ETAG: stream.etag, _HEADER_LEN: str(stream.content_length)}

        return StreamingResponse(
            stream.iter_content(1024*512),
            media_type=stream.content_type,
            headers=headers,
            background=background_task,
        )

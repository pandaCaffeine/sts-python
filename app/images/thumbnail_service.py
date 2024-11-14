from logging import Logger

from starlette import status
from starlette.responses import Response, StreamingResponse, JSONResponse

from app.config import BucketsMap, BucketSettings
from app.images.image_processor import resize_image
from app.images.storage_client import StorageClient, StorageFileItem

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"

NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                content={"detail": "File not found"})

__all__ = ['ThumbnailService']


class ThumbnailService:
    _storage_client: StorageClient
    _buckets_map: BucketsMap
    _logger: Logger

    def __init__(self, storage_client: StorageClient, buckets_map: BucketsMap, logger: Logger):
        assert storage_client is not None, "storage_client is required"
        assert buckets_map is not None, "buckets_map is required"
        assert logger is not None, "logger is required"

        self._storage_client = storage_client
        self._buckets_map = buckets_map
        self._logger = logger

    def make_thumbnail(self, bucket: str, file_name: str, etag: str | None) -> Response:
        bucket_settings = self._get_bucket_settings(bucket)
        # if bucket was not configured: the given bucket is not a source bucket and not a thumbnail bucket
        if not bucket_settings:
            self._logger.debug(f"Bucket {bucket} is not configured")
            return NOT_FOUND_RESPONSE

        source_file_stat = self._storage_client.get_file_stat(bucket_settings.source_bucket, file_name)
        if not source_file_stat:
            self._logger.debug("Source file was not found")
            return NOT_FOUND_RESPONSE

        if bucket == bucket_settings.source_bucket:
            return self._get_file_response(source_file_stat, etag)

        thumbnail_stat = self._storage_client.get_file_stat(bucket, file_name)
        if thumbnail_stat:
            if thumbnail_stat.parent_etag == source_file_stat.etag:
                self._logger.debug("Found thumbnail file")
                return self._get_file_response(thumbnail_stat, etag)

        image_data = self._storage_client.load_file(bucket_settings.source_bucket, file_name)
        self._logger.debug("Source file was loaded into memory")
        thumbnail = resize_image(image_data, bucket_settings.width, bucket_settings.height)
        if thumbnail.error:
            self._logger.warning(f"Failed to create thumbnail: {thumbnail.error}")
            return NOT_FOUND_RESPONSE

        self._logger.debug("Thumbnail file was created")
        put_result = self._storage_client.put_file(bucket, file_name, thumbnail.data,
                                                   content_type=thumbnail.content_type,
                                                   parent_etag=source_file_stat.etag)
        self._logger.debug("Thumbnail was uploaded to storage")

        headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
        return StreamingResponse(thumbnail.data, media_type=thumbnail.content_type,
                                 headers=headers)

    def make_thumbnail_by_alias(self, source_bucket: str, file_name: str, alias: str, etag: str | None) -> Response:
        if not source_bucket in self._buckets_map.all_source_buckets:
            self._logger.debug(f"Source bucket {source_bucket} was not found, return 404")
            return NOT_FOUND_RESPONSE

        bucket = self._buckets_map.alias_map.get(alias, source_bucket)
        return self.make_thumbnail(bucket, file_name, etag)

    def _get_bucket_settings(self, bucket: str) -> BucketSettings:
        if bucket == self._buckets_map.source_bucket:
            return self._buckets_map.buckets[bucket]

        return self._buckets_map.buckets.get(bucket, None)

    def _get_file_response(self, file_storage_item: StorageFileItem, etag: str | None) -> Response:
        if etag and file_storage_item.etag == etag:
            self._logger.debug(f"Requested file has the same etag: {etag}")
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        self._logger.debug("Etag is different, return file from bucket")
        object_stream = self._storage_client.open_stream(file_storage_item.directory, file_storage_item.file_name)
        if not object_stream:
            return NOT_FOUND_RESPONSE

        headers = {HEADER_ETAG: object_stream.etag, HEADER_LEN: object_stream.content_length}
        return StreamingResponse(object_stream.read_to_end(), media_type=object_stream.content_type, headers=headers)

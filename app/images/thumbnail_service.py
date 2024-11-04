import os
from io import BytesIO
from logging import Logger
from typing import Iterable

from starlette import status
from starlette.responses import Response, StreamingResponse, JSONResponse

from app.config import BucketsMap, BucketSettings
from app.images.image_processor import resize_image
from app.images.storage_client import StorageClient, StorageFileItem

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"

NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                content={"detail": "File not found"})

KEY_PARENT_ETAG = "x-amz-meta-parent-etag"


class ThumbnailService:
    __storage_client: StorageClient
    __buckets_map: BucketsMap
    __logger: Logger

    @staticmethod
    def __stream_bytes(data: BytesIO) -> Iterable[bytes]:
        data.seek(0, os.SEEK_SET)
        with data:
            buffer: bytes = data.read()
            while buffer and len(buffer) > 0:
                yield buffer
                buffer = data.read()

    def __init__(self, storage_client: StorageClient, buckets_map: BucketsMap, logger: Logger):
        assert storage_client is not None, "storage_client is required"
        assert buckets_map is not None, "buckets_map is required"
        assert logger is not None, "logger is required"

        self.__storage_client = storage_client
        self.__buckets_map = buckets_map
        self.__logger = logger

    def make_thumbnail(self, bucket: str, file_name: str, etag: str | None) -> Response:
        bucket_data = self._get_bucket_data(bucket)
        # if bucket was not configured: the given bucket is not a source bucket and not a thumbnail bucket
        if not bucket_data:
            self.__logger.debug(f"Bucket {bucket} is not configured")
            return NOT_FOUND_RESPONSE

        source_file_stat = self.__storage_client.get_file_stat(bucket_data.source_bucket, file_name)
        if not source_file_stat:
            self.__logger.debug("Source file was not found")
            return NOT_FOUND_RESPONSE

        if bucket == bucket_data.source_bucket:
            return self._get_file_response(source_file_stat, etag)

        thumbnail_stat = self.__storage_client.get_file_stat(bucket, file_name)
        parent_etag = thumbnail_stat.metadata.get(KEY_PARENT_ETAG, None)
        if thumbnail_stat and parent_etag == source_file_stat.etag:
            self.__logger.debug("Found thumbnail file")
            return self._get_file_response(thumbnail_stat, etag)

        image_data = self.__storage_client.load_file(bucket_data.source_bucket, file_name)
        self.__logger.debug("Source file was loaded into memory")
        thumbnail = resize_image(image_data, float(bucket_data.width), float(bucket_data.height))
        if thumbnail.error:
            self.__logger.warning(f"Failed to create thumbnail: {thumbnail.error}")
            return NOT_FOUND_RESPONSE

        self.__logger.debug("Thumbnail file was created")
        put_result = self.__storage_client.put_file(bucket, file_name, thumbnail.data,
                                                    content_type=thumbnail.content_type,
                                                    metadata={KEY_PARENT_ETAG: source_file_stat.etag})
        self.__logger.debug("Thumbnail was uploaded to storage")

        headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
        return StreamingResponse(self.__stream_bytes(thumbnail.data), media_type=thumbnail.content_type,
                                 headers=headers)

    def make_thumbnail_by_alias(self, source_bucket: str, file_name: str, alias: str, etag: str | None) -> Response:
        if not source_bucket in self.__buckets_map.all_source_buckets:
            self.__logger.debug(f"Source bucket {source_bucket} was not found, return 404")
            return NOT_FOUND_RESPONSE

        bucket = self.__buckets_map.alias_map.get(alias, source_bucket)
        return self.make_thumbnail(bucket, file_name, etag)

    def _get_bucket_data(self, bucket: str) -> BucketSettings:
        if bucket == self.__buckets_map.source_bucket:
            result = BucketSettings()
            result.source_bucket = bucket
            return result

        return self.__buckets_map.buckets.get(bucket, None)

    def _get_file_response(self, file_storage_item: StorageFileItem, etag: str | None) -> Response:
        if etag and file_storage_item.etag == etag:
            self.__logger.debug(f"Requested file has the same etag: {etag}")
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        self.__logger.debug("Etag is different, return file from bucket")
        object_stream = self.__storage_client.open_stream(file_storage_item.directory, file_storage_item.file_name)
        if not object_stream:
            return NOT_FOUND_RESPONSE

        headers = {HEADER_ETAG: object_stream.etag, HEADER_LEN: object_stream.etag}
        return StreamingResponse(object_stream.read_to_end(), media_type=object_stream.content_type, headers=headers)

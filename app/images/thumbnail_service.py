import os
from io import BytesIO
from logging import Logger
from typing import Iterable

from starlette import status
from starlette.responses import Response, StreamingResponse, JSONResponse

from app.config import BucketsMap
from app.images.image_processor import resize_image
from app.images.storage_client import StorageClient

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"

NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                content={"detail": "File not found"})


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

        thumbnail_stat = self.__storage_client.get_file_stat(bucket, file_name)
        if thumbnail_stat:
            self.__logger.debug("Found thumbnail file")
            if etag and thumbnail_stat.etag == etag:
                self.__logger.debug(f"Requested file has the same etag: {etag}")
                headers = {HEADER_ETAG: etag}
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

            self.__logger.debug("Etag is different, return file from bucket")
            r = self.__storage_client.open_stream(bucket, file_name)
            headers = {HEADER_ETAG: thumbnail_stat.etag, HEADER_LEN: str(thumbnail_stat.size)}
            return StreamingResponse(r.read_to_end(), media_type=thumbnail_stat.content_type, headers=headers)

        bucket_data = self.__buckets_map.buckets.get(bucket, None)
        if not bucket_data:
            self.__logger.debug(f"Configuration was not found for bucket {bucket}")
            return NOT_FOUND_RESPONSE

        source_bucket = bucket_data.source_bucket or self.__buckets_map.source_bucket
        source_file_stat = self.__storage_client.get_file_stat(source_bucket, file_name)
        if not source_file_stat:
            self.__logger.debug("Source file was not found, return 404")
            return NOT_FOUND_RESPONSE

        image_data = self.__storage_client.load_file(source_bucket, file_name)
        self.__logger.debug("Source file was loaded into memory")
        thumbnail = resize_image(image_data, float(bucket_data.width), float(bucket_data.height))
        if thumbnail.error:
            self.__logger.warning(f"Failed to create thumbnail: {thumbnail.error}")
            return NOT_FOUND_RESPONSE

        self.__logger.debug("Thumbnail file was created")
        put_result = self.__storage_client.put_file(bucket, file_name, thumbnail.data, content_type=thumbnail.content_type)
        self.__logger.debug("Thumbnail was uploaded to storage")

        headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
        return StreamingResponse(self.__stream_bytes(thumbnail.data), media_type=thumbnail.content_type, headers=headers)

    def make_thumbnail_by_alis(self, source_bucket: str, file_name: str, alias: str, etag: str | None) -> Response:
        if not source_bucket in self.__buckets_map.all_source_buckets:
            self.__logger.debug(f"Source bucket {source_bucket} was not found, return 404")
            return NOT_FOUND_RESPONSE

        bucket = self.__buckets_map.alias_map.get(alias, source_bucket)
        return self.make_thumbnail(bucket, file_name, etag)

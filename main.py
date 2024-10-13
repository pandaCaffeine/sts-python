import os
import sys
from functools import lru_cache
from io import BytesIO
from logging import Logger
from typing import Annotated, Generator

import uvicorn
from fastapi import FastAPI, Header, Response, status
from fastapi.params import Depends
from loguru import logger
from minio import Minio
from starlette.responses import StreamingResponse, JSONResponse

from config import app_settings
from storage_client import StorageClient, S3StorageClient
from image_processor import resize_image

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"

s3Client = Minio(endpoint=app_settings.s3.endpoint, access_key=app_settings.s3.access_key,
                 secret_key=app_settings.s3.secret_key, region=app_settings.s3.region,
                 cert_check=app_settings.s3.trust_cert, secure=app_settings.s3.use_tsl)

storage_client: StorageClient = S3StorageClient(s3Client)


def __stream_bytesio(data: BytesIO) -> Generator:
    data.seek(0, os.SEEK_SET)
    with data:
        buffer: bytes = data.read()
        while buffer and len(buffer) > 0:
            yield buffer
            buffer = data.read()


def __process_response(bucket: str, filename: str,
                       s3client: StorageClient,
                       l: Logger,
                       etag: str | None) -> Response:
    thumbnail_stat = s3client.get_file_stat(bucket, filename)
    if thumbnail_stat:
        l.debug("Found thumbnail file")
        if etag and thumbnail_stat.etag == etag:
            l.debug(f"Requested file has the same etag: {etag}")
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        l.debug("Etag is different, return file from bucket")
        r = s3client.open_stream(bucket, filename)
        headers = {HEADER_ETAG: thumbnail_stat.etag, HEADER_LEN: str(thumbnail_stat.size)}
        return StreamingResponse(r.read_to_end(), media_type=thumbnail_stat.content_type, headers=headers)

    bucket_data = app_settings.buckets[bucket]
    if bucket_data is None:
        l.debug(f"Configuration was not found for bucket {bucket}")
        return __NOT_FOUND_RESPONSE

    source_bucket = bucket_data.source_bucket or app_settings.source_bucket
    source_file_stat = s3client.get_file_stat(source_bucket, filename)
    if not source_file_stat:
        l.debug("Source file was not found, return 404")
        return __NOT_FOUND_RESPONSE

    image_data = s3client.load_file(source_bucket, filename)
    l.debug("Source file was loaded to memory")
    thumbnail = resize_image(image_data, float(bucket_data.width), float(bucket_data.height))
    if thumbnail.error:
        l.warning(f"Failed to create thumbnail: {thumbnail.error}")
        return __NOT_FOUND_RESPONSE

    l.debug("Thumbnail data was created")

    put_result = s3client.put_file(bucket, filename, thumbnail.data, content_type=thumbnail.mime_type)
    l.debug("Thumbnail image was uploaded to storage")
    headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
    return StreamingResponse(__stream_bytesio(thumbnail.data), media_type=thumbnail.mime_type, headers=headers)


__NOT_FOUND_RESPONSE: JSONResponse = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                  content={"detail": "File not found"})

app = FastAPI()


async def resolve_storage_client() -> StorageClient:
    return storage_client


async def resolve_logger(bucket: str, filename: str) -> Logger:
    return logger.bind(bucket=bucket, filename=filename, source="get_thumbnail")


@lru_cache
def get_source_buckets():
    result: list[str] = [app_settings.source_bucket]
    for bucket_cfg in app_settings.buckets.values():
        result.append(bucket_cfg.source_bucket)
    return result


@lru_cache()
def get_alias_map():
    result = dict[str, str]()
    for bucket_name, bucket_cfg in app_settings.buckets.items():
        if not bucket_cfg.alias:
            continue
        result[bucket_cfg.alias] = bucket_name
    return result


@app.get("/{bucket}/{filename}")
def get_thumbnail(bucket: str, filename: str,
                  s3client: Annotated[StorageClient, Depends(resolve_storage_client)],
                  l: Annotated[Logger, Depends(resolve_logger)],
                  etag: Annotated[str | None, Header(alias="If-None-Match")] = None):
    return __process_response(bucket, filename, s3client, l, etag)


@app.get("/{bucket}/{filename}/{alias}")
def get_thumbnail_for_alias(bucket: str, filename: str, alias: str,
                            source_buckets: Annotated[list[str], Depends(get_source_buckets)],
                            alias_map: Annotated[dict[str, str], Depends(get_alias_map)],
                            s3client: Annotated[StorageClient, Depends(resolve_storage_client)],
                            l: Annotated[Logger, Depends(resolve_logger)],
                            etag: Annotated[str | None, Header(alias="If-None-Match")] = None) -> Response:
    if not bucket in source_buckets:
        return __NOT_FOUND_RESPONSE

    bucket_name = alias_map.get(alias, bucket)
    return __process_response(bucket_name, filename, s3client, l, etag)


def __start_app():
    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level, format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level, retention="10 days", format=app_settings.log_fmt)

    l = logger.bind(source="core")

    buckets = app_settings.buckets
    if len(buckets) > 0:
        for bucket_name in buckets.keys():
            life_time_days = buckets[bucket_name].life_time_days
            bucket_created = storage_client.try_create_dir(bucket_name, life_time_days)
            if bucket_created:
                l.info(f"Bucket '{bucket_name}' was created with life time {life_time_days} days")
            else:
                l.info(f"Bucket '{bucket_name}' already exists, skip it")
    else:
        l.warning("No buckets were configured, exit")
        pass

    l.info("Starting web host")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    __start_app()

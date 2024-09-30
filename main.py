import os
from io import BytesIO
from typing import Annotated, Generator

import uvicorn
from PIL import Image
from fastapi import FastAPI, Header, Response, status, HTTPException
from fastapi.params import Depends
from minio import Minio, S3Error
from minio.datatypes import Object
from starlette.responses import StreamingResponse
from urllib3 import BaseHTTPResponse

from config import app_settings, AppSettings

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"
CONTENT_TYPE_JPEG = "image/jpeg"
FORMAT_JPEG = "JPEG"

s3Client = Minio(endpoint=app_settings.s3.endpoint, access_key=app_settings.s3.access_key,
                 secret_key=app_settings.s3.secret_key, region=app_settings.s3.region,
                 cert_check=app_settings.s3.trust_cert, secure=app_settings.s3.use_tsl)


async def get_settings() -> AppSettings:
    return app_settings


async def minio_client() -> Minio:
    return s3Client


app = FastAPI()


def stream_response(http_response: BaseHTTPResponse) -> Generator:
    try:
        source_stream = http_response.stream()
        for chunk in source_stream:
            yield chunk
    finally:
        http_response.close()


def stream_bytesio(data: BytesIO) -> Generator:
    data.seek(0, os.SEEK_SET)
    with data:
        buffer: bytes = data.read()
        while buffer and len(buffer) > 0:
            yield buffer
            buffer = data.read()


def test_file_in_bucket(s3client: Minio, bucket: str, object_name: str) -> Object | None:
    try:
        result = s3client.stat_object(bucket_name=bucket, object_name=object_name)
        return result
    except S3Error:
        return None


def read_file_to_memory(http_response: BaseHTTPResponse) -> BytesIO:
    result = BytesIO()
    try:
        data = http_response.stream()
        for chunk in data:
            result.write(chunk)
        result.seek(0, os.SEEK_SET)
        return result
    finally:
        http_response.close()
        http_response.release_conn()


@app.get("/{bucket}/{filename}")
def get_thumbnail(bucket: str, filename: str,
                  s3client: Annotated[Minio, Depends(minio_client)],
                  etag: Annotated[str | None, Header(alias="If-None-Match")] = None):
    s3resp: BaseHTTPResponse | None = None

    thumbnail_stat = test_file_in_bucket(s3client, bucket, filename)
    if thumbnail_stat:
        if etag and thumbnail_stat.etag == etag:
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        try:
            s3resp = s3client.get_object(bucket_name=bucket, object_name=filename)
            headers = {HEADER_ETAG: thumbnail_stat.etag, HEADER_LEN: str(thumbnail_stat.size)}
            return StreamingResponse(stream_response(s3resp), media_type=thumbnail_stat.content_type,
                                     headers=headers)
        finally:
            if s3resp:
                s3resp.release_conn()

    source_file_stat = test_file_in_bucket(s3client, app_settings.source_bucket, filename)
    if not source_file_stat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    try:
        s3resp = s3client.get_object(bucket_name=app_settings.source_bucket, object_name=filename)
        size = (float(app_settings.buckets[bucket].width), float(app_settings.buckets[bucket].height))
        with read_file_to_memory(s3resp) as source_data:
            with Image.open(source_data) as im:
                im.thumbnail(size)
                thumbnail_data = BytesIO()
                im.save(thumbnail_data, format=FORMAT_JPEG)

        thumbnail_data_size = thumbnail_data.tell()
        thumbnail_data.seek(0, os.SEEK_SET)
        put_result = s3client.put_object(bucket_name=bucket, object_name=filename, data=thumbnail_data,
                                         length=thumbnail_data_size, content_type=CONTENT_TYPE_JPEG)
        headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(thumbnail_data_size)}
        return StreamingResponse(stream_bytesio(thumbnail_data), media_type=CONTENT_TYPE_JPEG, headers=headers)
    finally:
        if s3resp:
            s3resp.close()
            s3resp.release_conn()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

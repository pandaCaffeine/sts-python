import os
from io import BytesIO
from typing import Annotated, Generator

import uvicorn
from Crypto.SelfTest.Cipher.test_CBC import file_name
from PIL import Image
from fastapi import FastAPI, Header, Response, status, HTTPException
from fastapi.params import Depends
from minio import Minio, S3Error
from minio.datatypes import Object
from starlette.responses import StreamingResponse
from urllib3 import BaseHTTPResponse

from config import app_settings, AppSettings
from storage_client import StorageClient, S3StorageClient, StorageResponse

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"
CONTENT_TYPE_JPEG = "image/jpeg"
FORMAT_JPEG = "JPEG"

s3Client = Minio(endpoint=app_settings.s3.endpoint, access_key=app_settings.s3.access_key,
                 secret_key=app_settings.s3.secret_key, region=app_settings.s3.region,
                 cert_check=app_settings.s3.trust_cert, secure=app_settings.s3.use_tsl)

storage_client: StorageClient = S3StorageClient(s3Client)


async def resolve_storage_client() -> StorageClient:
    return storage_client


app = FastAPI()


def stream_bytesio(data: BytesIO) -> Generator:
    data.seek(0, os.SEEK_SET)
    with data:
        buffer: bytes = data.read()
        while buffer and len(buffer) > 0:
            yield buffer
            buffer = data.read()


@app.get("/{bucket}/{filename}")
def get_thumbnail(bucket: str, filename: str,
                  s3client: Annotated[StorageClient, Depends(resolve_storage_client)],
                  etag: Annotated[str | None, Header(alias="If-None-Match")] = None):
    thumbnail_stat = s3client.get_file_stat(bucket, filename)
    if thumbnail_stat:
        if etag and thumbnail_stat.etag == etag:
            headers = {HEADER_ETAG: etag}
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        r = s3client.open_stream(bucket, filename)
        with r:
            headers = {HEADER_ETAG: thumbnail_stat.etag, HEADER_LEN: str(thumbnail_stat.size)}
            return StreamingResponse(r.read_to_end(), media_type=thumbnail_stat.content_type, headers=headers)

    source_file_stat = s3client.get_file_stat(app_settings.source_bucket, file_name)
    if not source_file_stat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    size = (float(app_settings.buckets[bucket].width), float(app_settings.buckets[bucket].height))
    image_mem = s3client.load_file(bucket, filename)
    with image_mem:
        with Image.open(image_mem) as im:
            im.thumbnail(size)
            thumbnail_data = BytesIO()
            im.save(thumbnail_data, format=FORMAT_JPEG)

    put_result = s3client.put_file(bucket, filename, thumbnail_data, content_type=CONTENT_TYPE_JPEG)
    headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
    return StreamingResponse(stream_bytesio(thumbnail_data), media_type=CONTENT_TYPE_JPEG, headers=headers)


if __name__ == "__main__":
    buckets = app_settings.buckets
    if len(buckets) > 0:
        for bucket_name in buckets.keys():
            storage_client.try_create_dir(bucket_name)
    else:
        pass

    uvicorn.run(app, host="0.0.0.0", port=8000)

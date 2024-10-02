import os
from io import BytesIO
from typing import Annotated, Generator

import uvicorn
from PIL import Image
from fastapi import FastAPI, Header, Response, status
from fastapi.params import Depends
from minio import Minio
from starlette.responses import StreamingResponse, JSONResponse

from config import app_settings
from storage_client import StorageClient, S3StorageClient

HEADER_ETAG = "Etag"
HEADER_LEN = "Content-Length"
CONTENT_TYPE_JPEG = "image/jpeg"
FORMAT_JPEG = "JPEG"

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


def __resize_image(data: BytesIO, width: float, height: float) -> BytesIO:
    with data:
        with Image.open(data) as im:
            im.thumbnail((width, height))
            result = BytesIO()
            im.save(result, format=FORMAT_JPEG)
            return result


app = FastAPI()


async def resolve_storage_client() -> StorageClient:
    return storage_client


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
        headers = {HEADER_ETAG: thumbnail_stat.etag, HEADER_LEN: str(thumbnail_stat.size)}
        return StreamingResponse(r.read_to_end(), media_type=thumbnail_stat.content_type, headers=headers)

    source_file_stat = s3client.get_file_stat(app_settings.source_bucket, filename)
    if not source_file_stat:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "File not found"})

    image_data = s3client.load_file(app_settings.source_bucket, filename)
    thumbnail_data = __resize_image(image_data, float(app_settings.buckets[bucket].width),
                                    float(app_settings.buckets[bucket].height))

    put_result = s3client.put_file(bucket, filename, thumbnail_data, content_type=CONTENT_TYPE_JPEG)
    headers = {HEADER_ETAG: put_result.etag, HEADER_LEN: str(put_result.size)}
    return StreamingResponse(__stream_bytesio(thumbnail_data), media_type=CONTENT_TYPE_JPEG, headers=headers)


if __name__ == "__main__":
    buckets = app_settings.buckets
    if len(buckets) > 0:
        for bucket_name in buckets.keys():
            storage_client.try_create_dir(bucket_name)
    else:
        pass

    uvicorn.run(app, host="0.0.0.0", port=8000)

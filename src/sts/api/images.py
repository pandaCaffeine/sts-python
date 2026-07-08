"""Image thumbnails HTTP API.

Routes for retrieving image thumbnails from configured storage buckets.
All endpoints respect the standard ``If-None-Match`` request header
(RFC 9110) for client-side caching: when the supplied ETag matches the
current object ETag, the service replies with ``304 Not Modified`` and
without body.
"""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaSyncRoute
from fastapi import APIRouter, Header, Response

from sts.images.thumbnail import ThumbnailService

images_router = APIRouter(route_class=DishkaSyncRoute)

_EtagDep = Annotated[str | None, Header(alias="If-None-Match")]


@images_router.get("/{bucket}/{file_name}",
                   summary="Return a file from a source or thumbnail bucket",
                   description=(
                           "Return the file stored at ``{bucket}/{file_name}``.\n\n"
                           "The bucket kind is resolved from configuration:\n\n"
                           "- **Source bucket** — the original file is streamed back as is.\n"
                           "- **Thumbnail bucket** — if a processed thumbnail already "
                           "exists in storage, it is streamed back; if only the source "
                           "file is present, a new thumbnail is generated on demand from "
                           "the source and streamed back.\n\n"
                           "Supports ETag-based caching via ``If-None-Match``: when the "
                           "supplied ETag matches the current object ETag, the response "
                           "is ``304 Not Modified`` and no body is returned."
                   ),
                   responses={
                       200: {"description": "Thumbnail bytes streamed back successfully"},
                       304: {"description": "Not modified; client's cached version is still valid"},
                       400: {"description": "Invalid bucket or file name"},
                       404: {"description": "Neither the source nor a cached thumbnail exists"},
                       422: {"description": "Validation error for path or header parameters"},
                   },
                   tags=["thumbnails"],
                   )
def get_thumbnail(bucket: str, file_name: str,
                  thumbnail_service: FromDishka[ThumbnailService],
                  etag: _EtagDep = None) -> Response:
    """Return the file stored at ``{bucket}/{file_name}`` for any bucket kind.

    The endpoint transparently serves both source buckets and thumbnail
    buckets; the bucket role is resolved from configuration:

    - **Source bucket** — the original file is streamed back as is.
    - **Thumbnail bucket** — if a processed thumbnail already exists in
      storage, it is streamed back; if only the source file is present,
      a new thumbnail is generated on demand from the source file and
      streamed back.

    Supports ETag-based caching via ``If-None-Match``: if the supplied
    ETag matches the current object ETag, the response is ``304 Not
    Modified`` and no body is returned.

    Args:
        bucket: Target bucket name. Works for source buckets (returns
            the original file) and thumbnail buckets (returns an existing
            or freshly generated thumbnail).
        file_name: Object name within the bucket, including any extension.
        thumbnail_service: Injected thumbnail service handling storage I/O
            and on-demand thumbnail creation.
        etag: Optional ``If-None-Match`` value for conditional responses.

    Returns:
        A ``200 OK`` streaming response with the source or thumbnail bytes,
        ``304 Not Modified`` if ``etag`` matches the current object ETag,
        or ``404 Not Found`` if neither the source nor a cached thumbnail
        exists in the requested bucket.
    """
    return thumbnail_service.get_thumbnail(bucket, file_name, etag)


@images_router.get("/{source_bucket}/{file_name}/{alias}",
                   summary="Get thumbnail resolved through a bucket alias",
                   description=(
                           "Return a thumbnail resolved through a bucket alias.\n\n"
                           "The real bucket is looked up by `alias` within `source_bucket`; "
                           "then the same lookup-and-serve flow as `get_thumbnail` is used. "
                           "Supports ETag-based caching via `If-None-Match`."
                   ),
                   responses={
                       200: {"description": "Thumbnail bytes streamed back successfully"},
                       304: {"description": "Not modified; client's cached version is still valid"},
                       400: {"description": "Invalid bucket, file name, or alias"},
                       404: {"description": "Alias is unknown or the file does not exist"},
                       422: {"description": "Validation error for path or header parameters"},
                   },
                   tags=["thumbnails"],
                   )
def get_thumbnail_by_alias(source_bucket: str, file_name: str, alias: str,
                           thumbnail_service: FromDishka[ThumbnailService],
                           etag: _EtagDep = None) -> Response:
    """Return a thumbnail resolved through a bucket alias.

    The real bucket is looked up by ``alias`` within ``source_bucket``;
    then the same lookup-and-serve flow as :func:`get_thumbnail` is used.
    Supports ETag-based caching via ``If-None-Match``.

    Args:
        source_bucket: Bucket in which the alias is registered; not the bucket
            the thumbnail itself is read from.
        file_name: Object name within the resolved bucket, including any extension.
        alias: Alias pointing to the target bucket inside ``source_bucket``.
        thumbnail_service: Injected thumbnail service handling storage I/O.
        etag: Optional ``If-None-Match`` value for conditional responses.

    Returns:
        A ``200 OK`` streaming response with the thumbnail bytes,
        ``304 Not Modified`` if ``etag`` matches the current object ETag,
        or ``404 Not Found`` if the alias is unknown or the file does not exist.
    """
    return thumbnail_service.get_thumbnail_by_alias(source_bucket, file_name, alias, etag)

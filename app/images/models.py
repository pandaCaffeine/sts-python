import enum
from dataclasses import dataclass
from io import BytesIO


class BucketStatus(str, enum.Enum):
    created = "created",
    exists = "exists",
    error = "error"


@dataclass
class BucketsInfo:
    thumbnail_buckets: dict[str, str]
    source_buckets: dict[str, str]


@dataclass(frozen=True)
class ImageData:
    content_type: str
    error: Exception | None = None
    data: BytesIO | None = None

import enum
from dataclasses import dataclass

class ImageFormat(enum.StrEnum):
    NONE = enum.auto()
    PNG = enum.auto()
    JPEG = enum.auto()

class BucketStatus(str, enum.Enum):
    created = "created",
    exists = "exists",
    error = "error"


@dataclass(slots=True)
class BucketsInfo:
    thumbnail_buckets: dict[str, str]
    source_buckets: dict[str, str]
    error: bool
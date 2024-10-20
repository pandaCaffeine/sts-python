from dataclasses import dataclass
from io import BytesIO


@dataclass(frozen=True)
class ImageData:
    content_type: str
    error: Exception | None = None
    data: BytesIO | None = None

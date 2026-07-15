from io import BytesIO

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(frozen=True, slots=True, config=ConfigDict(arbitrary_types_allowed=True))
class ImageData:
    content_type: str
    error: Exception | None = None
    data: BytesIO | None = None

from dataclasses import dataclass
from io import BytesIO

import PIL
from PIL import Image


@dataclass(frozen=True)
class ImageData:
    mime_type: str
    error: Exception | None = None
    data: BytesIO | None = None


def resize_image(data: BytesIO, width: float, height: float) -> ImageData:
    assert data is not None, "data cannot be None"
    assert width > 0, "width must be greater than 0"
    assert height > 0, "height must be greater than 0"

    with data:
        try:
            with Image.open(data) as im:
                mime_type = im.get_format_mimetype()

                im.thumbnail((width, height))
                result = BytesIO()
                im.save(result, im.format, optimize=True)
                return ImageData(mime_type=mime_type, error=None, data=result)
        except (PIL.UnidentifiedImageError, ValueError, TypeError, Exception) as e:
            return ImageData(mime_type=mime_type, error=e, data=None)

from io import BytesIO

import PIL
from PIL import Image

from sts.images.models import ImageData


def resize_image(data: BytesIO, width: int, height: int) -> ImageData:
    assert data is not None, "data cannot be None"
    assert width > 0, "width must be greater than 0"
    assert height > 0, "height must be greater than 0"

    with data:
        try:
            with Image.open(data) as im:
                mime_type = im.get_format_mimetype()

                new_size: tuple[float, float] = (float(width), float(height))
                im.thumbnail(new_size)
                result = BytesIO()
                im.save(result, im.format, optimize=True)
                return ImageData(content_type=mime_type, error=None, data=result)
        except (PIL.UnidentifiedImageError, ValueError, TypeError, Exception) as e:
            return ImageData(content_type=mime_type, error=e, data=None)

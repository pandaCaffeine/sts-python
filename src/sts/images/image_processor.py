import functools
from io import BytesIO
from typing import Any

import PIL
import anyio.to_thread
from PIL import Image, ImageFile

from sts.images.models import ImageData
from sts.models import ImageFormat

_default_params: dict[str, Any] = {'optimize': True}
_format_modes: dict[ImageFormat, str] = {
    ImageFormat.JPEG: 'RGB',
    ImageFormat.PNG: 'P'
}


def _try_convert_image(source_image: PIL.ImageFile.ImageFile, new_mode: str) -> PIL.Image.Image:
    if source_image.mode == new_mode:
        return source_image

    new_image: PIL.Image.Image | None = None
    try:
        new_image = source_image.convert(new_mode)
        if source_image != new_image:
            source_image.close()

        return new_image
    except (ValueError, Exception):
        if new_image:
            new_image.close()
        return source_image


def resize_image(data: BytesIO,
                 width: int,
                 height: int,
                 image_format: ImageFormat = ImageFormat.NONE,
                 params: dict[str, Any] | None = None) -> ImageData:
    assert data is not None, "data cannot be None"
    assert width > 0, "width must be greater than 0"
    assert height > 0, "height must be greater than 0"

    save_params = params or _default_params

    with data:
        try:
            with Image.open(data) as im:
                mime_type = im.get_format_mimetype()
                new_size: tuple[float, float] = (float(width), float(height))
                im.thumbnail(new_size)

                if image_format != ImageFormat.NONE:
                    dest_mode = _format_modes[image_format]
                    im = _try_convert_image(im, dest_mode)
                    im.format = str(image_format)
                    mime_type = Image.MIME.get(im.format.upper())

                result = BytesIO()
                im.save(result, im.format, **save_params)
                return ImageData(content_type=mime_type, error=None, data=result)
        except (PIL.UnidentifiedImageError, ValueError, TypeError, Exception) as e:
            return ImageData(content_type=mime_type, error=e, data=None)

async def resize_image_async(data: BytesIO,
                 width: int,
                 height: int,
                 image_format: ImageFormat = ImageFormat.NONE,
                 params: dict[str, Any] | None = None) -> ImageData:
    func = functools.partial(resize_image, data=data, width=width, height=height, image_format=image_format, params=params)
    return await anyio.to_thread.run_sync(func, ())


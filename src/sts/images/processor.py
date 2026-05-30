"""
Image processing utilities for thumbnail generation and format conversion.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from sts.models.enums import ImageFormat
from sts.models.file_storage import ImageData

# Default compression parameters for image saving
_DEFAULT_SAVE_PARAMS: dict[str, Any] = {"optimize": True}

# PIL color mode mapping for target image formats
_FORMAT_MODES: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "RGB",
    ImageFormat.PNG: "P",
}


def _apply_mode(
        img: Image.Image,
        mode: str | None
) -> Image.Image:
    """
    Convert image to specified color mode if necessary.
    Returns the converted image or None if conversion is not needed.
    Preserves the source image if conversion fails.
    """
    if not mode or img.mode == mode:
        return img

    try:
        return img.convert(mode)
    except (ValueError, OSError):
        return img


def _safe_close_image(image: Image.Image | None) -> None:
    """Safely close an image if it has a close method."""
    if image is not None and hasattr(image, "close"):
        try:
            image.close()
        except Exception:
            pass


def resize_image(
        data: BytesIO,
        width: int,
        height: int,
        image_format: ImageFormat = ImageFormat.NONE,
        params: dict[str, Any] | None = None,
) -> ImageData:
    """
    Resize image data to specified dimensions.

    Args:
        data: Input image data as BytesIO stream.
        width: Target width in pixels (must be > 0).
        height: Target height in pixels (must be > 0).
        image_format: Optional target format conversion.
        params: Optional parameters passed to PIL save method.

    Returns:
        ImageData with resized image or error information.
    """

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be > 0")

    result_image: Image.Image | None = None
    mime_type = ""

    try:
        with Image.open(data) as source:
            mime_type = source.get_format_mimetype() or mime_type

            source.thumbnail((width, height))
            result_image = source

            if image_format != ImageFormat.NONE:
                target_mode = _FORMAT_MODES.get(image_format)
                if target_mode:
                    result_image = _apply_mode(source, target_mode)
                    result_image.format = str(image_format.value)
                    mime_type = Image.MIME.get(image_format.value.upper(), mime_type)

            assert result_image is not None
            output = BytesIO()
            result_image.save(output, result_image.format, **(params or _DEFAULT_SAVE_PARAMS))

            return ImageData(content_type=mime_type, error=None, data=output)
    except Exception as e:
        _safe_close_image(result_image)
        return ImageData(content_type=mime_type, error=e, data=None)

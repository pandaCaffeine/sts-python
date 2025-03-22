from io import BytesIO
from PIL import Image

from sts.images.image_processor import resize_image
from sts.models import ImageFormat


_mime_png = 'image/png'
_mime_jpeg = 'image/jpeg'
_mode_rgb = 'RGB'
_format_png = 'PNG'

def __read_file(file_name: str) -> BytesIO:
    with open(file_name, 'rb') as file_data:
        return BytesIO(file_data.read())


def test_resize_image() -> None:
    file_data = __read_file('test.png')
    resize_result = resize_image(file_data, 100, 100)

    assert not resize_result.error
    assert resize_result.content_type == _mime_png
    assert resize_result.data

    with resize_result.data:
        with Image.open(resize_result.data) as image:
            assert image.size[0] == 100
            assert image.size[1] == 100
            assert image.format == _format_png


def test_resize_image_png2jpeg() -> None:
    file_data = __read_file('test.png')
    resize_result = resize_image(file_data, 100, 100, image_format=ImageFormat.JPEG)

    assert not resize_result.error
    assert resize_result.content_type == _mime_jpeg
    assert resize_result.data

    with resize_result.data:
        with Image.open(resize_result.data) as image:
            assert image.size[0] == 100
            assert image.size[1] == 100
            assert image.mode == _mode_rgb
            assert image.get_format_mimetype() == _mime_jpeg

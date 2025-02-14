from io import BytesIO
from PIL import Image

from sts.images.image_processor import resize_image


def __read_file(file_name: str) -> BytesIO:
    with open(file_name, "rb") as file_data:
        return BytesIO(file_data.read())


def test_resize_image() -> None:
    file_data = __read_file("test.png")
    resize_result = resize_image(file_data, 100, 100)

    assert not resize_result.error
    assert resize_result.content_type == "image/png"
    assert resize_result.data

    with resize_result.data:
        with Image.open(resize_result.data) as image:
            assert image.size[0] == 100
            assert image.size[1] == 100

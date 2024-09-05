import io
from pathlib import Path

import requests
from PIL import Image


def url_to_pil(url: str) -> Image.Image:
    image_bytes = requests.get(url).content
    bytes_obj = io.BytesIO(image_bytes)
    return Image.open(bytes_obj)


def url_show_image(url: str):
    url_to_pil(url).show()


def url_save_image(url: str) -> str:
    image_bytes = requests.get(url).content
    filename = url.split('/')[-1]
    Path(filename).write_bytes(image_bytes)
    return filename

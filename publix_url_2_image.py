import io
import re
from dataclasses import dataclass
from typing import Self

import requests
from PIL import Image


# sample url
# https://akimages.shoplocal.com/dyn_li/1080.0.80.20/Retailers/Publix/240824ES_01_img_113884010.jpg
#           change the image width here ^^^^

def _update_url_width(url: str, width: int) -> str:
    # Use regex to find and replace the first number before the pattern '.number.number.number/'
    updated_url = re.sub(r'(\d+)(\.\d+\.\d+\.\d+/)', f'{width}\\2', url)
    return updated_url


@dataclass(frozen=True)
class PublixURL2Image:
    url: str

    def with_width(self, new_width: int) -> Self:
        new_url = _update_url_width(self.url, new_width)
        return PublixURL2Image(new_url)

    def to_pil(self) -> Image.Image:
        image_bytes = requests.get(self.url).content
        bytes_obj = io.BytesIO(image_bytes)
        return Image.open(bytes_obj)

    def show(self):
        self.to_pil().show()

    def save(self) -> str:
        filename = self.url.split('/')[-1]
        self.to_pil().save(filename)
        return filename

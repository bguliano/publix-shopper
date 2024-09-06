import re
from dataclasses import dataclass
from typing import Self

import requests
from PIL import Image


# sample url
# https://akimages.shoplocal.com/dyn_li/1080.0.80.20/Retailers/Publix/240824ES_01_img_113884010.jpg
#           change the image width here ^^^^
#                                        change to coupon image here ^

# max regular image width is 600
# max coupon image width is 1300

def _update_url_width(url: str, width: int) -> str:
    # Use regex to find and replace the first number before the pattern '.number.number.number/'
    updated_url = re.sub(r'(\d+)(\.\d+\.\d+\.\d+/)', f'{width}\\2', url)
    return updated_url


def _add_coupon_component(url: str) -> str:
    components = url.split('/')
    components.insert(-1, 'Coupons')
    return '/'.join(components)


@dataclass(frozen=True)
class PublixURL2Image:
    url: str

    def attempt_new_width(self, new_width: int) -> Self:
        new_url = _update_url_width(self.url, new_width)
        return PublixURL2Image(new_url)

    def to_coupon(self) -> Self:
        new_url = _add_coupon_component(self.url)
        return PublixURL2Image(new_url)

    def to_pil(self) -> Image.Image:
        image_bytes = requests.get(self.url, stream=True).raw
        return Image.open(image_bytes)

    def show(self):
        self.to_pil().show()

    def save(self) -> str:
        filename = self.url.split('/')[-1]
        self.to_pil().save(filename)
        return filename


if __name__ == '__main__':
    url = 'https://akimages.shoplocal.com/dyn_li/150.0.88.0/Retailers/Publix/240824ES_11_CPN_98.jpg'
    PublixURL2Image(url).attempt_new_width(5000).to_coupon().show()

import io
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image
from bs4 import BeautifulSoup, Tag

URL = 'https://accessibleweeklyad.publix.com/PublixAccessibility/Entry/LandingContent?storeid=2501023'
BASE_URL = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(URL))


@dataclass(frozen=True)
class DepartmentItem:
    listing_id: int
    title: str
    deal: str
    additional_deal_info: str
    valid_dates: str
    contain_redemption_info: str
    coupon_api_terms: str
    description: str
    image_url: str

    def save_image(self) -> str:
        image_bytes = requests.get(self.image_url).content
        Path(filename := f'{self.title}.png').write_bytes(image_bytes)
        return filename

    def show_image(self):
        image_bytes = requests.get(self.image_url).content
        bytes_obj = io.BytesIO(image_bytes)
        Image.open(bytes_obj).show()


class Department:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.items = []

        self._parse_listing()

    @staticmethod
    def _get_tag_text(container_tag: Tag, tag_name: str, class_name: str) -> str:
        try:
            return container_tag.find(tag_name, class_=class_name).text.strip().replace('â', '')
        except AttributeError:
            print(f'No {class_name} found...', end='', flush=True)
            return ''

    def _parse_listing(self):
        content = requests.get(self.url).content
        soup = BeautifulSoup(content, features='html.parser')
        item_containers: list[Tag] = soup.find_all('div', class_='theTileContainer')
        for container in item_containers:
            self._parse_item(container)

    def _parse_item(self, container: Tag):
        raw_style = container.find('img').get('style')
        image_url = 'https:' + re.search(r'url\(([^)]+)\)', raw_style).group(1)
        title = self._get_tag_text(container, 'div', 'title')
        print(f'{self.name} - {title}...', end='', flush=True)
        self.items.append(DepartmentItem(
            listing_id=int(container.get('data-listingid')),
            title=title,
            deal=self._get_tag_text(container, 'div', 'deal'),
            additional_deal_info=self._get_tag_text(container, 'div', 'additionalDealInfo'),
            valid_dates=self._get_tag_text(container, 'div', 'validDates'),
            contain_redemption_info=self._get_tag_text(container, 'div', 'containRedemptionInfo'),
            coupon_api_terms=self._get_tag_text(container, 'p', 'couponAPITerms'),
            description=self._get_tag_text(container, 'div', 'description'),
            image_url=image_url
        ))
        print('Parsed')


def get_department_links(soup: BeautifulSoup) -> list[Department]:
    container = soup.find('div', class_='infoUnit')
    anchors = container.find_all('a', class_='listing')
    return [Department(a.text.strip(), BASE_URL + a.get('href')) for a in anchors]


def main() -> None:
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, features='html.parser')
    links = get_department_links(soup)
    pass


if __name__ == '__main__':
    main()

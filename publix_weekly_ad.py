import atexit
import difflib
import itertools
import pickle
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Self
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from publix_store_info import PublixStoreInfo


@dataclass(frozen=True)
class PublixDeal:
    listing_id: int
    title: str
    deal: Optional[str]
    additional_deal_info: Optional[str]
    valid_dates: Optional[str]
    contain_redemption_info: Optional[str]
    coupon_api_terms: Optional[str]
    description: Optional[str]
    image_url: str
    is_coupon: bool

    def __eq__(self, other):
        return self.title == other.title


SortedDeals = dict[str, list[PublixDeal]]
UnsortedDeals = list[PublixDeal]


class PublixWeeklyAd:
    default_export_path = 'export_weekly_ad.pkl'

    def __init__(self, *, store_id: int):
        self.store_id = store_id
        self._sorted_deals: SortedDeals = {}
        atexit.register(self.export)

        # if export not found, go straight to regenerate deals and exit
        if not (filepath := Path(self.default_export_path)).exists():
            self.regenerate_deals()
            return

        # import deals
        data = filepath.read_bytes()
        old_weekly_ad: PublixWeeklyAd = pickle.loads(data)
        self._sorted_deals = old_weekly_ad._sorted_deals

        # if deals have not expired, return
        unique_dates = set(x.valid_dates for x in self.unsorted_deals if x.valid_dates)
        today = datetime.now().date()
        earliest_expiry_date = min(
            datetime.strptime(
                re.search(r'(\d{1,2}/\d{1,2})\s*$', text).group(1), '%m/%d'
            ).replace(year=today.year).date()
            for text in unique_dates
        )
        if earliest_expiry_date >= today:
            return

        # if here, then search for new deals
        self.regenerate_deals()

    @classmethod
    def from_store_num(cls, store_num: int) -> Self:
        store_info = PublixStoreInfo(store_num)
        return cls(store_id=store_info.store_id)

    def regenerate_deals(self):
        self._sorted_deals.clear()

        # create url with selected store number
        url = 'https://accessibleweeklyad.publix.com/PublixAccessibility/Entry/LandingContent?storeid={}'
        url = url.format(self.store_id)

        # GET HTML response and parse with bs4
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features='html.parser')
        container = soup.find('div', class_='infoUnit')
        anchors = container.find_all('a', class_='listing')

        # create and parse each listing URL
        listing_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
        self._sorted_deals = {
            a.text.strip(): list(self._parse_listing(listing_url + a.get('href')))
            for a in anchors
        }

    def _parse_listing(self, url: str) -> Generator[PublixDeal, None, None]:
        print(f'Parsing "{url}"...', end='', flush=True)
        content = requests.get(url).content.decode('utf-8')
        soup = BeautifulSoup(content, features='html.parser')
        item_containers: list[Tag] = soup.find_all('div', class_='theTileContainer')
        for container in item_containers:
            yield self._parse_item(container)
        print('Done')

    @staticmethod
    def _get_tag_text(container_tag: Tag, tag_name: str, class_name: str) -> Optional[str]:
        try:
            return container_tag.find(tag_name, class_=class_name).text.strip()
        except AttributeError:
            # print(f'No {class_name} found...', end='', flush=True)
            return None

    def _parse_item(self, container: Tag) -> PublixDeal:
        raw_style = container.find('img').get('style')
        image_url = 'https:' + re.search(r'url\(([^)]+)\)', raw_style).group(1)
        title = self._get_tag_text(container, 'div', 'title')
        return PublixDeal(
            listing_id=int(container.get('data-listingid')),
            title=title,
            deal=self._get_tag_text(container, 'div', 'deal'),
            additional_deal_info=self._get_tag_text(container, 'div', 'additionalDealInfo'),
            valid_dates=self._get_tag_text(container, 'div', 'validDates'),
            contain_redemption_info=self._get_tag_text(container, 'div', 'containRedemptionInfo'),
            coupon_api_terms=self._get_tag_text(container, 'p', 'couponAPITerms'),
            description=self._get_tag_text(container, 'div', 'description'),
            image_url=image_url,
            is_coupon=container.find('a', class_='printcouponlink') is not None
        )

    @property
    def sorted_deals(self) -> SortedDeals:
        return self._sorted_deals.copy()

    @property
    def unsorted_deals(self) -> UnsortedDeals:
        return list(set(itertools.chain.from_iterable(self._sorted_deals.values()))).copy()

    def export(self) -> str:
        data = pickle.dumps(self)
        (filepath := Path(self.default_export_path)).write_bytes(data)
        return str(filepath)

    def find_best_matches(self, query: str) -> tuple[PublixDeal, ...]:
        # Extract the titles from the deals
        all_items = self.unsorted_deals
        all_titles = map(lambda x: x.title, all_items)

        # calculate similarity ratios
        best_matches = difflib.get_close_matches(query, all_titles, n=3, cutoff=0.1)

        # Find the corresponding Deal objects
        return tuple(filter(lambda x: x.title in best_matches, all_items))


if __name__ == '__main__':
    pwa = PublixWeeklyAd.from_store_num(1095)

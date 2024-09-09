import itertools
import json
import pickle
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Self, Any

import requests

from publix_store_info import PublixStoreInfo


@dataclass(frozen=True)
class PublixProductDeal:
    description: str
    value_description: str
    expiration_date: str


@dataclass
class PublixProduct:
    name: str
    code: str
    image_url: str
    location: str
    deal: Optional[PublixProductDeal]
    quantity: Optional[float] = None

    def __eq__(self, other):
        return self.name == other.name

    def is_low(self) -> bool:
        return self.quantity < 0.2

    @property
    def percent_left(self) -> str:
        if not self.quantity:
            return 'No quantity supplied'
        return f'{round(self.quantity * 100)}% left'

    @property
    def percent_used(self) -> str:
        if not self.quantity:
            return 'No quantity supplied'
        return f'{round((1 - self.quantity) * 100)}% used'


SortedProducts = dict[str, list[PublixProduct]]
UnsortedProducts = list[PublixProduct]


class PublixGroceryList:
    default_export_path = 'export_grocery_list.pkl'

    def __init__(self, grocery_list_id: str, store_num: int, sorted_products: SortedProducts):
        self.grocery_list_id = grocery_list_id
        self.store_num = store_num
        self._sorted_products = sorted_products

    @classmethod
    def from_id(cls, grocery_list_id: str, store_num: int) -> Self:
        # make request to publix api
        base_url = 'https://services.publix.com/api/v1/GroceryList/GetListWithSavings?groceryListId={}'
        formatted_id = urllib.parse.quote(grocery_list_id)
        response = requests.get(base_url.format(formatted_id), headers={'Publixstore': str(store_num)})
        json_response = response.json()

        # begin formatting json response
        result = {}
        for location_dict in json_response['locations']:
            result[location_dict['name']] = [
                PublixProduct(
                    name=item_dict['Name'],
                    code=item_dict['ProductItemCode'],
                    image_url=item_dict['ImageUrl'],
                    location=item_dict['Location'],
                    deal=PublixProductDeal(
                        description=item_dict['PriceDescription'],
                        value_description=item_dict['ValueDescription'],
                        expiration_date=item_dict['PriceExpirationDate']
                    ) if item_dict['PriceDescription'] else None
                )
                for item_dict in location_dict['items']
            ]
        return cls(grocery_list_id, store_num, result)

    @classmethod
    def from_cookie(cls, cookie: dict[str, Any], store_num: int) -> Self:
        unquoted = urllib.parse.unquote(cookie['value'])
        grocery_list_id = json.loads(unquoted)['id']
        return cls.from_id(grocery_list_id, store_num)

    @classmethod
    def import_(cls) -> Optional[Self]:
        if not (filepath := Path(cls.default_export_path)).exists():
            return None
        data = filepath.read_bytes()
        return pickle.loads(data)

    @property
    def sorted_products(self) -> SortedProducts:
        return self._sorted_products.copy()

    @property
    def unsorted_products(self) -> UnsortedProducts:
        return list(itertools.chain.from_iterable(self._sorted_products.values())).copy()

    def __len__(self) -> int:
        return len(self.unsorted_products)

    def export(self) -> str:
        data = pickle.dumps(self)
        (filepath := Path(self.default_export_path)).write_bytes(data)
        return str(filepath)

    def update_from(self, other_grocery_list: Self):
        # can't just use dict.update since that removes quantity values
        original_products = self.unsorted_products

        # update quantity values if necessary
        for product_list in other_grocery_list._sorted_products.values():
            for product in product_list:
                # only update quantity value if it doesn't already exist
                if product.quantity:
                    continue

                # attempt to find matching PublixProduct
                try:
                    idx = original_products.index(product)
                except ValueError:
                    continue

                # if found, update
                product.quantity = original_products[idx].quantity

        # set current dict to updated dict
        self._sorted_products = other_grocery_list._sorted_products

    def print(self):
        store_info = PublixStoreInfo(self.store_num)
        print(f'{store_info.name} ({store_info.address}):')
        longest_product_name = max((len(x.name) for x in self.unsorted_products))
        for location, products in self._sorted_products.items():
            print(f'\t{location}:')
            for product in products:
                print(f'\t{" !! " if product.deal else "\t"}{product.name:<{longest_product_name}} - '
                      f'{product.percent_left}')
            print()


if __name__ == '__main__':
    if gl := PublixGroceryList.import_():
        gl.print()
    else:
        print('No export file found')

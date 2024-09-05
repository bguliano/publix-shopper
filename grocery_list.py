import itertools
import json
import pickle
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Self, Any

import requests


@dataclass(frozen=True)
class PublixStoreInformation:
    raw: dict[str, Any]
    store_num: int
    name: str
    image_url: str
    address: str
    phone_number: str


@dataclass
class PublixProduct:
    name: str
    code: str
    image_url: str
    location: str
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


class GroceryList:
    default_export_path = 'grocery_list_export.pkl'

    def __init__(self, store_num: int, sorted_products: dict[str, list[PublixProduct]]):
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
                    location=item_dict['Location']
                )
                for item_dict in location_dict['items']
            ]
        return cls(store_num, result)

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

    @classmethod
    def new(cls, store_num: int) -> Self:
        return cls(store_num, dict())

    @property
    def sorted_products(self) -> dict[str, list[PublixProduct]]:
        return self._sorted_products.copy()

    @property
    def unsorted_products(self) -> list[PublixProduct]:
        return list(itertools.chain.from_iterable(self._sorted_products.values())).copy()

    @property
    def store_information(self) -> PublixStoreInformation:
        # request GET
        base_url = 'https://services.publix.com/storelocator/api/v1/stores/?storeNumber={}&count=1'
        response = requests.get(base_url.format(self.store_num))
        response_json: dict[str, Any] = response.json()

        # parse
        store_json = response_json['stores'][0]
        return PublixStoreInformation(
            raw=store_json.copy(),
            store_num=int(store_json['storeNumber']),
            name=store_json['name'],
            image_url=store_json['image']['hero'],
            address=', '.join(store_json['address'].values()),
            phone_number=store_json['phoneNumbers']['Store']
        )

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
        store_info = self.store_information
        print(f'{store_info.name} ({store_info.address}):')
        longest_product_name = max((len(x.name) for x in self.unsorted_products))
        for location, products in self._sorted_products.items():
            print(f'\t{location}:')
            for product in products:
                print(f'\t\t{product.name:<{longest_product_name}} - {product.percent_left}')
            print()


if __name__ == '__main__':
    gl = GroceryList.import_()
    if gl:
        gl.print()
    else:
        print('No export file found')

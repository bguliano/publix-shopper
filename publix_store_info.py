from typing import Any

import requests


class PublixStoreInfo:
    def __init__(self, store_num: int):
        # request GET
        base_url = 'https://services.publix.com/storelocator/api/v1/stores/?storeNumber={}&count=1'
        response = requests.get(base_url.format(store_num))
        response_json: dict[str, Any] = response.json()

        # parse
        store_json = response_json['stores'][0]
        self.raw = store_json.copy()
        self.store_num = int(store_json['storeNumber'])
        self.name = store_json['name']
        self.image_url = store_json['image']['hero']
        self.address = ', '.join(store_json['address'].values())
        self.phone_number = store_json['phoneNumbers']['Store']
        self.store_id = int(store_json['weeklyAd']['storeId'])


if __name__ == '__main__':
    psi = PublixStoreInfo(1095)

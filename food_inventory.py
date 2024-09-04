import atexit
import io
import json
import pickle
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Optional

import requests
from PIL import Image
from selenium import webdriver


@dataclass
class PublixProduct:
    name: str
    code: str
    image_url: str
    location: str

    def save_image(self) -> str:
        image_bytes = requests.get(self.image_url).content
        Path(filename := f'{self.name}.png').write_bytes(image_bytes)
        return filename

    def show_image(self):
        image_bytes = requests.get(self.image_url).content
        bytes_obj = io.BytesIO(image_bytes)
        Image.open(bytes_obj).show()


class WebDriverGetShoppingListCookie:
    def __init__(self, driver: webdriver.Chrome, cookie_dict: dict):
        self._thread = Thread(target=self._check_driver, args=(driver, cookie_dict))

    def wait(self):
        self._thread.start()
        self._thread.join()

    @staticmethod
    def _check_driver(driver: webdriver.Chrome, cookie_dict: dict):
        while driver.window_handles:
            if potential_cookie := driver.get_cookie('GroceryList'):
                cookie_dict.update(potential_cookie)
            time.sleep(1)


class PublixScraper:
    def __init__(self, *, store_num: int = 1095):
        self.store_num = store_num

        print('Initializing webdriver...', end='', flush=True)
        options = webdriver.ChromeOptions()
        # allows injection of GroceryList cookie before page loads
        options.page_load_strategy = 'none'
        self.driver = webdriver.Chrome(options)
        print('Done')

        self.grocery_list_cookie = {}
        atexit.register(self.save_grocery_list_cookie)

    def save_grocery_list_cookie(self):
        cookie_data = pickle.dumps(self.grocery_list_cookie)
        Path('grocery_list_cookie.pkl').write_bytes(cookie_data)

    @property
    def grocery_list_id(self) -> Optional[str]:
        if not self.grocery_list_cookie:
            return

        unquoted = urllib.parse.unquote(self.grocery_list_cookie['value'])
        return json.loads(unquoted)['id']

    def get_grocery_list(self) -> dict[str, list[PublixProduct]]:
        # early exit if no grocery list id
        if not (grocery_list_id := self.grocery_list_id):
            return {}

        # make request to publix api
        base_url = 'https://services.publix.com/api/v1/GroceryList/GetListWithSavings?groceryListId={}'
        formatted_id = urllib.parse.quote(grocery_list_id)
        response = requests.get(base_url.format(formatted_id), headers={'Publixstore': str(self.store_num)})
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
        return result

    def start(self):
        self.driver.get(f'https://www.publix.com?setstorenumber={self.store_num}')

        if (cookie_path := Path('grocery_list_cookie.pkl')).exists():
            cookie_data = cookie_path.read_bytes()
            self.grocery_list_cookie.update(pickle.loads(cookie_data))
            self.driver.add_cookie(self.grocery_list_cookie)

        WebDriverGetShoppingListCookie(self.driver, self.grocery_list_cookie).wait()


if __name__ == '__main__':
    ps = PublixScraper()
    ps.start()

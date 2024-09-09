import atexit
import json
import time
from threading import Thread
from typing import Optional

from selenium import webdriver

import webdriver_tools
from publix_grocery_list import PublixGroceryList


class WebDriverWatchGroceryList(Thread):
    def __init__(self, driver: webdriver.Chrome, store_num: int):
        Thread.__init__(self)
        self.driver = driver
        self.store_num = store_num
        self.grocery_list: Optional[PublixGroceryList] = PublixGroceryList.import_()

    def watch(self) -> Optional[PublixGroceryList]:
        # first, inject grocery list cookie if grocery list exists
        if self.grocery_list:
            atexit.register(self.grocery_list.export)
            cookie_data = json.dumps({'id': self.grocery_list.grocery_list_id})
            self.driver.add_cookie({
                'name': 'GroceryList',
                'value': cookie_data,
                'domain': '.publix.com'
            })
            self.driver.add_cookie({
                'name': 'ShoppingListCount',
                'value': str(len(self.grocery_list)),
                'domain': '.publix.com'
            })

        # then, start the thread
        self.start()
        self.join()

        # give back grocery list
        return self.grocery_list

    def get_shopping_list_count(self) -> int:
        if not (cookie := webdriver_tools.safe_get_cookie(self.driver, 'ShoppingListCount')):
            return 0
        return int(cookie['value'])

    def ask_quantity(self, product_name: str) -> float:
        def is_valid(x: Optional[str]):
            if not x:
                return False

            try:
                if x.endswith('%'):
                    y = int(x[:-1]) / 100
                else:
                    y = float(x)
            except ValueError:
                return False

            return 0 <= y <= 1

        while not is_valid(inpt := webdriver_tools.prompt(self.driver, f'How much {product_name} do you have?')):
            webdriver_tools.alert(
                self.driver,
                'Please enter a decimal between 0 and 1 or percentage between 0% and 100%'
            )

        if inpt.endswith('%'):
            return float(inpt[:-1]) / 100
        return float(inpt)

    def update_grocery_list(self):
        # first, update grocery list
        cookie = webdriver_tools.safe_get_cookie(self.driver, 'GroceryList')
        new_list = PublixGroceryList.from_cookie(cookie, self.store_num)
        if self.grocery_list:
            self.grocery_list.update_from(new_list)
        else:
            self.grocery_list = new_list

        # second, prompt user if necessary
        for product in self.grocery_list.unsorted_products:
            if product.quantity:
                continue
            quantity = self.ask_quantity(product.name)
            product.quantity = quantity

        # third, save changes
        self.grocery_list.export()

    def run(self) -> None:
        # only run while driver is open
        while self.driver.window_handles:

            # check if shopping list has changed
            count = self.get_shopping_list_count()
            if count > 0 and not self.grocery_list:
                self.update_grocery_list()
            elif self.grocery_list and len(self.grocery_list) != count:
                self.update_grocery_list()

            # sleep to prevent spam
            time.sleep(1)


class PublixInventory:
    def __init__(self, *, store_num: int = 1095):
        self.store_num = store_num

        print('Initializing webdriver...', end='', flush=True)
        options = webdriver.ChromeOptions()
        # allows injection of GroceryList cookie before page loads
        options.page_load_strategy = 'none'
        self.driver = webdriver.Chrome(options)
        print('Done')

    def start(self):
        self.driver.get(f'https://www.publix.com?setstorenumber={self.store_num}')

        # wait until user closes the browser
        grocery_list = WebDriverWatchGroceryList(self.driver, self.store_num).watch()

        # save and print out new grocery list
        print()
        grocery_list.print()


if __name__ == '__main__':
    ps = PublixInventory()
    ps.start()

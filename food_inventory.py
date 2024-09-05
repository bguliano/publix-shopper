import atexit
import pickle
import time
from pathlib import Path
from threading import Thread

from selenium import webdriver

from grocery_list import GroceryList


def ask_float_question(question: str, min_: float, max_: float) -> float:
    def is_float(x):
        try:
            float(x)
        except ValueError:
            return False
        return True

    while not is_float(inpt := input(question)) and (min_ <= float(inpt) <= max_):
        print(f'Please enter a float between {min_} and {max_}')

    return float(inpt)


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

        self.grocery_list = GroceryList.import_()
        if not self.grocery_list:
            self.grocery_list = GroceryList.new(store_num)
        atexit.register(self.grocery_list.export)

    def save_grocery_list_cookie(self):
        # pickle cookie_data
        cookie_data = pickle.dumps(self.grocery_list_cookie)
        Path('grocery_list_cookie.pkl').write_bytes(cookie_data)

    def start(self):
        self.driver.get(f'https://www.publix.com?setstorenumber={self.store_num}')

        # add grocery list cookie to driver if it exists
        if (cookie_path := Path('grocery_list_cookie.pkl')).exists():
            cookie_data = cookie_path.read_bytes()
            self.grocery_list_cookie.update(pickle.loads(cookie_data))
            self.driver.add_cookie(self.grocery_list_cookie)

        # wait until user closes the browser
        WebDriverGetShoppingListCookie(self.driver, self.grocery_list_cookie).wait()

        # update current grocery list with new ones from this session
        new_grocery_list = GroceryList.from_cookie(self.grocery_list_cookie, self.store_num)
        self.grocery_list.merge(new_grocery_list)

        # ask user how much of each item should be added to list
        for product in self.grocery_list.unsorted_products:
            if product.quantity:
                continue
            quantity = ask_float_question(f'How much of {product.name} do you have?', 0, 1)
            product.quantity = quantity

        # save and print out new grocery list
        self.grocery_list.export()
        self.grocery_list.print()


if __name__ == '__main__':
    ps = PublixScraper()
    ps.start()

from typing import Optional

from selenium import webdriver
from selenium.common import NoAlertPresentException
from selenium.webdriver.support.wait import WebDriverWait


def prompt(driver: webdriver.Chrome, prompt_text: str) -> str:
    prompt_js = f'_webdriver_prompt_result = prompt("{prompt_text}");'
    get_prompt_js = 'return _webdriver_prompt_result;'

    def alert_not_present(driver: webdriver.Chrome) -> bool:
        try:
            _ = driver.switch_to.alert.text
            return False
        except NoAlertPresentException:
            return True

    driver.execute_script(prompt_js)
    WebDriverWait(driver, float('inf')).until(alert_not_present)
    return driver.execute_script(get_prompt_js)


def alert(driver: webdriver.Chrome, alert_text: str):
    alert_js = f'alert("{alert_text}");'

    def alert_not_present(driver: webdriver.Chrome) -> bool:
        try:
            _ = driver.switch_to.alert.text
            return False
        except NoAlertPresentException:
            return True

    driver.execute_script(alert_js)
    WebDriverWait(driver, float('inf')).until(alert_not_present)


def safe_get_cookie(driver: webdriver.Chrome, cookie_name: str) -> Optional[dict]:
    # occasionally, the driver will be closed but due to timings, the code will still
    # try to grab information from the window (like cookies), so this function helps
    # prevent crashes
    if not driver.window_handles:
        return None
    return driver.get_cookie(cookie_name)

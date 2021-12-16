from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
import selenium.common.exceptions

import time
import sys
import csv
import os
import os.path
import datetime
import requests
import json


PRODUCT_IDS = [
    '147719', # Trotineta electrica Blaupunkt
    '143800', # Combina frigorifica Arctic
    '144043', # Combina frigorifica Beko
]
CSV_DIR = 'flanco_csv'


def getBrowserDriver(selenium_host):
    op = webdriver.ChromeOptions()
    op.add_argument('--no-sandbox')
    op.add_argument('--disable-dev-shm-usage')
    op.add_argument("--headless") # run without GUI
    op.add_argument('--blink-settings=imagesEnabled=false') # don't load images

    # driver = webdriver.Chrome(service_log_path=os.path.join(os.getcwd(), "browser_service_log.txt"), options=op)
    # driver = webdriver.Chrome(options=op)

    # service = Service(ChromeDriverManager().install())
    # service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    # driver = webdriver.Chrome(service=service, 
    #                           service_log_path=os.path.join(os.getcwd(), "browser_service_log.txt"), 
    #                           options=op)>

    # driver = webdriver.Remote("http://127.0.0.1:4444/wd/hub", DesiredCapabilities.CHROME)
    url = f"http://{selenium_host}:4444/wd/hub"
    print(f"url = {url}")
    driver = webdriver.Remote(command_executor=url, options=op)
    # driver = webdriver.Remote(command_executor="http://127.0.0.1:4444/wd/hub", desired_capabilities=op.to_capabilities())
    # driver = webdriver.Remote(command_executor="http://127.0.0.1:4444/wd/hub", desired_capabilities={'browserName': 'chrome'}, options=op)

    return driver

def findElement(driver, cssSelectors):
    for selector in cssSelectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return element
        except selenium.common.exceptions.NoSuchElementException:
            continue
        except:
            print("Got unexpected error while trying to find element based on css_selector:", sys.exc_info())
    
    return None

def waitForElement(driver, cssSelectors):
    try:
        WebDriverWait(driver, 50).until(lambda driver: findElement(driver, cssSelectors) is not None)
    except selenium.common.exceptions.TimeoutException:
        raise ValueError(f"Timed-out while waiting for element with any css-selector: {cssSelectors}")

def savePrice(selenium_host, site_url, product_ids, csv_dir):
    print(f"Getting driver on host:{selenium_host}")
    driver = getBrowserDriver(selenium_host)
    print(f"Got driver on host:{selenium_host}")

    # driver.get('https://hoopshype.com/salaries/players/')
    # print(len(driver.find_elements(By.CSS_SELECTOR, "td.name")))
    # return

    try:
        driver.get(site_url)

        for prod_id in product_ids:

            # navigate to product page
            search_field = driver.find_element(By.ID, "searchingfield")
            search_field.send_keys(prod_id)
            search_field.send_keys(Keys.ENTER)


            # get product price
            price_element_css_selectors = [
                "div.product-info-price div.price-box .singlePrice span.price", # pret simplu
                "div.product-info-price div.price-box div.pricesPrp .special-price span.price" # pret cu reducere (pret cu reducere sau cu PLP)
            ]
            waitForElement(driver, price_element_css_selectors)

            priceElement = findElement(driver, price_element_css_selectors)
            assert priceElement is not None

            price = priceElement.text
            price = ''.join(c for c in price if c.isdigit() or c in [',', '.'])
            curr_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            curr_url = driver.current_url

            print("prod_id =", prod_id)
            print("priceElement.text =", priceElement.text)
            print("price =", price)
            print("curr_date =", curr_date)
            print("curr_url =", curr_url)
            print()


            #write to CSV
            with open(os.path.join(csv_dir, f"product{prod_id}.csv"), mode='a') as csv_file:
                price_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                price_writer.writerow([str(prod_id), str(price), curr_date, curr_url])
    finally:
        driver.quit()
    
def is_selenium_container_ready(host):
    try:
        req = requests.get(f"http://{host}:4444/wd/hub/status")
        return json.loads(req.text)['value']['ready']
    except:
        return False

def wait_until(condition, *args, interval=0.1, timeout=1):
    start = time.time()
    while time.time() - start < timeout:
        if condition(*args):
            return True
        time.sleep(interval)
    
    return False


if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_directory)

    selenium_host = os.environ.get("SELENIUM_HOST", "localhost")
    timeout = 10

    print(f"Waiting for selenium host: {selenium_host}...")
    if not wait_until(is_selenium_container_ready, selenium_host, timeout=timeout):
        print(f"Timed-out after {timeout} seconds while waiting for host({selenium_host}). Abort...")
        sys.exit(-1)
    print(f"Host({selenium_host}) is up!")

    flanco_url = os.environ.get("FLANCO_URL", "https://www.flanco.ro/")

    savePrice(selenium_host, flanco_url, PRODUCT_IDS, os.path.join(script_directory, CSV_DIR))



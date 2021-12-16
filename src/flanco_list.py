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
import argparse
import urllib.parse


TEST_PRODUCT_IDS = [
    '147719', # Trotineta electrica Blaupunkt
    '143800', # Combina frigorifica Arctic
    '144043', # Combina frigorifica Beko
]
CSV_DIR = './shared_dir/flanco_csv/'


def getArgumentParser():
    parser = argparse.ArgumentParser(description='Start scraping Flanco in one of a few modes of operation')
    parser.add_argument("--verbose", "-v", action="store_true")

    subparsers = parser.add_subparsers(dest="subparser_name", help="The kind of run mode")
    subparsers.required = True

    parser_test = subparsers.add_parser("test", 
                                        help=f"Scrapes a short pre-defined list of product ids ({TEST_PRODUCT_IDS})")

    parser_list = subparsers.add_parser("list", help="Give a list of product ids for which to scrape prices")
    parser_list.add_argument("products", nargs="+", help="A list of product ids for which to scrape prices")

    parser_category = subparsers.add_parser("category", help="Give a category of products (as URL relative to host) for which to scrape prices")
    parser_category.add_argument("category_url", help="A category of products (as URL relative to host) for which to scrape prices")
    
    return parser


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

def waitForSeleniumContainer(selenium_host, timeout):
    print(f"Waiting for selenium host: {selenium_host} for {timeout} seconds...")
    if not wait_until(is_selenium_container_ready, selenium_host, timeout=timeout):
        print(f"Timed-out after {timeout} seconds while waiting for host({selenium_host}). Abort...")
        sys.exit(-1)
    print(f"Host({selenium_host}) is up!")
    print()


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

    url = f"http://{selenium_host}:4444/wd/hub"
    if args.verbose: print(f"Attempting to connect to selenium browser at URL = {url}")
    driver = webdriver.Remote(command_executor=url, options=op)

    return driver

def findElement(top, cssSelector):
    try:
        element = top.find_element(By.CSS_SELECTOR, cssSelector)
        return element
    except selenium.common.exceptions.NoSuchElementException:
        pass
    except:
        print("Got unexpected error while trying to find element based on css_selector:", sys.exc_info())
    
    return None

def getPricesFromPriceBox(priceBox):
    flanco_price_css = [
        (".singlePrice span.price", ".singlePrice span.price"), # simple price
        ("div.pricesPrp .pretVechiTaiat span.price", "div.pricesPrp .special-price span.price"), # reduced price #1
        ("div.pricesPrp .pretVechi .pricePrp span.price", "div.pricesPrp .special-price span.price"), # reduced price #2
    ]

    for css in flanco_price_css:
        try:
            unreduced_price = priceBox.find_element(By.CSS_SELECTOR, css[0])
            curr_price = priceBox.find_element(By.CSS_SELECTOR, css[1])
            return (unreduced_price, curr_price)
        except:
            continue
    
    return None

def waitForElement(driver, cssSelector):
    try:
        WebDriverWait(driver, 50).until(lambda driver: findElement(driver, cssSelector) is not None)
    except selenium.common.exceptions.TimeoutException:
        raise ValueError(f"Timed-out while waiting for element with css-selector: {cssSelector}")

def addPriceEntryToCSV(driver, csv_dir, prod_id, unreduced_price, curr_price):
    curr_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    curr_url = driver.current_url

    if args.verbose:
        print("prod_id =", prod_id)
        print("unreduced_price =", unreduced_price)
        print("curr_price =", curr_price)
        print("curr_date =", curr_date)
        print("curr_url =", curr_url)
        print()

    with open(os.path.join(csv_dir, f"product{prod_id}.csv"), mode='a') as csv_file:
        price_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        price_writer.writerow([str(prod_id), curr_date, unreduced_price, curr_price, curr_url])

def savePriceForList(driver, site_url, csv_dir, product_ids):
    driver.get(site_url)

    for prod_id in product_ids:

        # navigate to product page
        search_field = driver.find_element(By.ID, "searchingfield")
        search_field.send_keys(prod_id)
        search_field.send_keys(Keys.ENTER)


        # get product price
        price_box_css = "div.product-info-price div.price-box"
        waitForElement(driver, price_box_css)

        priceBox = findElement(driver, price_box_css)
        assert priceBox is not None
        priceTuple = getPricesFromPriceBox(priceBox)
        assert priceTuple is not None

        unreduced_price = priceTuple[0].text
        unreduced_price = ''.join(c for c in unreduced_price if c.isdigit() or c in [',', '.'])
        curr_price = priceTuple[1].text
        curr_price = ''.join(c for c in curr_price if c.isdigit() or c in [',', '.'])

        addPriceEntryToCSV(driver, csv_dir, prod_id, unreduced_price, curr_price)

def savePriceForCategory(driver, site_url, csv_dir, category_url):
    url = urllib.parse.urljoin(site_url, category_url)
    if args.verbose: print(f"Scraping category at {url}")
    driver.get(url)
    
    product_box_css = "li.product-item"
    waitForElement(driver, product_box_css)

    product_boxes = driver.find_elements(By.CSS_SELECTOR, product_box_css)
    if args.verbose: print(f"Found {len(product_boxes)} products on current page")
    
    print()
    for prod_box in product_boxes:

        # get product id
        prod_id_html_attribute = "data-product-sku"
        prod_id_element = prod_box.find_element(By.CSS_SELECTOR, f"*[{prod_id_html_attribute}]")
        assert prod_id_element is not None
        prod_id = prod_id_element.get_attribute(prod_id_html_attribute)

        # get price
        price_box_css = "div.price-box"
        priceBox = findElement(prod_box, price_box_css)
        assert priceBox is not None

        priceTuple = getPricesFromPriceBox(priceBox)
        assert priceTuple is not None

        unreduced_price = priceTuple[0].text
        unreduced_price = ''.join(c for c in unreduced_price if c.isdigit() or c in [',', '.'])
        curr_price = priceTuple[1].text
        curr_price = ''.join(c for c in curr_price if c.isdigit() or c in [',', '.'])

        # write to CSV
        addPriceEntryToCSV(driver, csv_dir, prod_id, unreduced_price, curr_price)

    # TODO press next

def startScraping(selenium_host):
    flanco_url = os.environ.get("FLANCO_URL", "https://www.flanco.ro/")
    csv_dir = os.path.join(script_directory, CSV_DIR)

    print(f"Getting driver on host:{selenium_host}")
    driver = getBrowserDriver(selenium_host)
    print(f"Got driver on host:{selenium_host}")
    print()

    # driver.get('https://hoopshype.com/salaries/players/')
    # print(len(driver.find_elements(By.CSS_SELECTOR, "td.name")))
    # return

    try:
        if not os.path.exists(csv_dir):
            os.mkdir(csv_dir)

        if args.subparser_name == "test":
            savePriceForList(driver, flanco_url, csv_dir, TEST_PRODUCT_IDS)
        elif args.subparser_name == "list":
            savePriceForList(driver, flanco_url, csv_dir, args.products)
        elif args.subparser_name == "category":
            savePriceForCategory(driver, flanco_url, csv_dir, args.category_url)
    finally:
        driver.quit()

if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_directory)

    global args
    args = getArgumentParser().parse_args()
    if args.verbose: print(args); print()

    selenium_host = os.environ.get("SELENIUM_HOST", "localhost")
    waitForSeleniumContainer(selenium_host=selenium_host, timeout=10)
    startScraping(selenium_host)



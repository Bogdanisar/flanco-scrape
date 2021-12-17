from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
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
WAIT_ELEMENT_TIMEOUT = 10 # seconds
WAIT_SELENIUM_TIMEOUT = 10 # seconds
CSV_ENTRY_LOG_INTERVAL = 200
SUBPARSER_TEST = "test"
SUBPARSER_LIST = "list"
SUBPARSER_CATEGORY = "category"
SUBPARSER_ENTIRE = "entire"

class MaxCSVEntryReached(ValueError):
    pass


def getArgumentParser():
    parser = argparse.ArgumentParser(description='Start scraping Flanco in one of a few modes of operation')
    parser.add_argument("--verbose", "-v", action='count', default=0)
    parser.add_argument("--max-entries", "-m", action="store", type=int, help="The maximum amount of CSV entries that this script will write before exiting")

    subparsers = parser.add_subparsers(dest="subparser_name", help="The kind of run mode")
    subparsers.required = True

    parser_test = subparsers.add_parser(SUBPARSER_TEST, 
                                        help=f"Scrapes a short pre-defined list of product ids ({TEST_PRODUCT_IDS})")

    parser_list = subparsers.add_parser(SUBPARSER_LIST, help="Give a list of product ids for which to scrape prices")
    parser_list.add_argument("products", nargs="+", help="A list of product ids for which to scrape prices")

    parser_category = subparsers.add_parser(SUBPARSER_CATEGORY, help="Give a category of products (as URL relative to host) for which to scrape prices")
    parser_category.add_argument("category_url", help="A category of products (as URL relative to host) for which to scrape prices")

    parser_entire = subparsers.add_parser(SUBPARSER_ENTIRE, help="Attempt to parse all products (up to the number of max-entries, if specified)")
    
    return parser


def is_selenium_container_ready(host, port):
    try:
        req = requests.get(f"http://{host}:{port}/wd/hub/status")
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

def waitForSeleniumContainer(selenium_host, selenium_port, timeout):
    print(f"Waiting for selenium host: {selenium_host} for {timeout} seconds...")
    if not wait_until(is_selenium_container_ready, selenium_host, selenium_port, timeout=timeout):
        print(f"Timed-out after {timeout} seconds while waiting for host({selenium_host}). Abort...")
        sys.exit(-1)
    print(f"Host({selenium_host}) is up!")
    print()


def getBrowserDriver(selenium_host, selenium_port):
    op = webdriver.ChromeOptions()
    op.add_argument('--no-sandbox')
    op.add_argument('--disable-dev-shm-usage')
    op.add_argument("--headless") # run without GUI
    op.add_argument('--blink-settings=imagesEnabled=false') # don't load images

    url = f"http://{selenium_host}:{selenium_port}/wd/hub"
    if args.verbose >= 1: print(f"Attempting to connect to selenium browser at URL = {url}")
    driver = webdriver.Remote(command_executor=url, options=op)

    return driver

def findElement(top, cssSelector):
    try:
        element = top.find_element(By.CSS_SELECTOR, cssSelector)
        return element
    except selenium.common.exceptions.NoSuchElementException:
        pass
    except selenium.common.exceptions.StaleElementReferenceException:
        print("Skipping stale element in find...")
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
        except selenium.common.exceptions.NoSuchElementException:
            continue
        except:
            print("Got unexpected error while getting prices:", sys.exc_info())
            raise
    
    return None

def waitForElement(driver, cssSelector):
    try:
        WebDriverWait(driver, WAIT_ELEMENT_TIMEOUT).until(lambda driver: findElement(driver, cssSelector) is not None)
    except selenium.common.exceptions.TimeoutException:
        raise ValueError(f"Timed-out while waiting for element with css-selector: {cssSelector}")
    
def waitForDocumentLoad(driver):
    try:
        condition = 'document.readyState == "complete"'
        documentIsLoaded = lambda driver: driver.execute_script(f"return {condition};")
        WebDriverWait(driver, WAIT_ELEMENT_TIMEOUT).until(documentIsLoaded)
    except selenium.common.exceptions.TimeoutException:
        raise ValueError(f"Timed-out while waiting for ({condition})")

def addPriceEntryToCSV(csv_dir, prod_id, unreduced_price, curr_price, prod_url):
    if args.max_entries is not None and addPriceEntryToCSV.count >= args.max_entries:
        raise MaxCSVEntryReached(f"Already reached maximum amount of CSV entries({args.max_entries})")

    curr_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    if args.verbose >= 2:
        print("prod_id =", prod_id)
        print("unreduced_price =", unreduced_price)
        print("curr_price =", curr_price)
        print("curr_date =", curr_date)
        print("curr_url =", prod_url)
        print()

    with open(os.path.join(csv_dir, f"product{prod_id}.csv"), mode='a') as csv_file:
        price_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        price_writer.writerow([str(prod_id), curr_date, unreduced_price, curr_price, prod_url])

    addPriceEntryToCSV.count = addPriceEntryToCSV.count + 1
    if addPriceEntryToCSV.count - addPriceEntryToCSV.lastLogAt >= CSV_ENTRY_LOG_INTERVAL:
        print(f"Added {addPriceEntryToCSV.count} CSV entries so far")
        addPriceEntryToCSV.lastLogAt = addPriceEntryToCSV.count

addPriceEntryToCSV.count = 0
addPriceEntryToCSV.lastLogAt = 0

def savePriceForList(driver, site_url, csv_dir, product_ids):
    driver.get(site_url)

    for prod_id in product_ids:

        # navigate to product page
        search_field = driver.find_element(By.ID, "searchingfield")
        search_field.send_keys(prod_id)
        search_field.send_keys(Keys.ENTER)

        # get product price
        price_box_css = "div.product-info-price div.price-box"
        waitForDocumentLoad(driver)
        waitForElement(driver, price_box_css)

        priceBox = findElement(driver, price_box_css)
        assert priceBox is not None
        priceTuple = getPricesFromPriceBox(priceBox)
        assert priceTuple is not None

        unreduced_price = priceTuple[0].text
        unreduced_price = ''.join(c for c in unreduced_price if c.isdigit() or c in [',', '.'])
        curr_price = priceTuple[1].text
        curr_price = ''.join(c for c in curr_price if c.isdigit() or c in [',', '.'])

        # write to CSV
        addPriceEntryToCSV(csv_dir, prod_id, unreduced_price, curr_price, driver.current_url)

def savePriceForCategory(driver, site_url, csv_dir, category_url, prod_id_set = None):
    driver.get(category_url)
    if args.verbose >= 1: print(f"Scraping category at {category_url}")
    
    skipAmount = 0
    pageNumber = 1
    while True:
        product_box_css = "li.product-item"
        waitForDocumentLoad(driver)
        try:
            waitForElement(driver, product_box_css)
        except ValueError:
            print("Couldn't find any product_box_css on page. Move to next category...")
            break

        product_boxes = driver.find_elements(By.CSS_SELECTOR, product_box_css)
        if args.verbose >= 1: print(f"Found {len(product_boxes)} products on page {pageNumber}")
        if args.verbose >= 2: print()

        for prod_box in product_boxes:

            try:
                # get product id
                prod_id_html_attribute = "data-product-sku"
                prod_id_element = prod_box.find_element(By.CSS_SELECTOR, f"*[{prod_id_html_attribute}]")
                assert prod_id_element is not None
                prod_id = prod_id_element.get_attribute(prod_id_html_attribute)

                if prod_id_set is not None and prod_id in prod_id_set:
                    skipAmount += 1
                    continue

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

                # get product url
                anchor = findElement(prod_box, "a.product-item-link")
                assert anchor is not None
                prod_url = anchor.get_attribute("href")

                # write to CSV
                addPriceEntryToCSV(csv_dir, prod_id, unreduced_price, curr_price, prod_url)

                # remember the id
                prod_id_set.add(prod_id)

            except selenium.common.exceptions.StaleElementReferenceException:
                if 'prod_id' not in locals():
                    prod_id = "N/A"
                print(f"Skipping stale element: Product ID is {prod_id} ...")
            except MaxCSVEntryReached:
                raise
            except:
                if 'prod_id' not in locals():
                    prod_id = "N/A"
                print(f"Got exception for Product ID {prod_id}: {sys.exc_info()}")

        try:
            nextButton = findElement(driver, "a.action.next:not(.mobile-filter-container a)")
            if nextButton is None:
                break
            
            driver.execute_script("arguments[0].click();", nextButton)
            pageNumber = pageNumber + 1
        except selenium.common.exceptions.StaleElementReferenceException:
            print("Next button was stale. Going to the next category...\n")
            break
        except:
            print("Unexpected error with 'Next' button:", sys.exc_info())
    
    if args.verbose >= 1: print(f"Skipped {skipAmount} known products in this category"); print()

def savePriceEntire(driver, site_url, csv_dir):
    driver.get(site_url)
    if args.verbose >= 1: print(f"Starting scraping {site_url}")


    category_anchors_css = "div.heromenu div.heromenu-content div.heromenu-content-category-wrapper div.heromenu-content-category-list li a"
    waitForDocumentLoad(driver)
    waitForElement(driver, category_anchors_css)
    category_anchors = driver.find_elements(By.CSS_SELECTOR, category_anchors_css)

    if args.verbose >= 1: print(f"Found {len(category_anchors)} categories"); print()

    category_url_list = []
    for anchor in category_anchors:
        category_url_list.append(anchor.get_attribute("href"))
    
    prod_id_set = set()
    for category_url in category_url_list:
        savePriceForCategory(driver, site_url, csv_dir, category_url, prod_id_set)


def startScraping(selenium_host, selenium_port):
    flanco_url = os.environ.get("FLANCO_URL", "https://www.flanco.ro/")
    csv_dir = os.path.join(script_directory, CSV_DIR)

    print(f"Getting driver on host:{selenium_host}")
    driver = getBrowserDriver(selenium_host, selenium_port)
    print(f"Got driver on host:{selenium_host}")
    print()

    try:
        if not os.path.exists(csv_dir):
            os.mkdir(csv_dir)

        if args.subparser_name == SUBPARSER_TEST:
            savePriceForList(driver, flanco_url, csv_dir, TEST_PRODUCT_IDS)
        elif args.subparser_name == SUBPARSER_LIST:
            savePriceForList(driver, flanco_url, csv_dir, args.products)
        elif args.subparser_name == SUBPARSER_CATEGORY:
            category_url = urllib.parse.urljoin(flanco_url, args.category_url)
            savePriceForCategory(driver, flanco_url, csv_dir, category_url, set())
        elif args.subparser_name == SUBPARSER_ENTIRE:
            savePriceEntire(driver, flanco_url, csv_dir)
        else:
            assert False
    except MaxCSVEntryReached as e:
        print("Stopping because:", str(e))
    finally:
        driver.quit()

if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_directory)

    global args
    args = getArgumentParser().parse_args()
    if args.verbose >= 1: print(args); print()

    selenium_host = os.environ.get("SELENIUM_HOST", "localhost")
    selenium_port = os.environ.get("SELENIUM_PORT", "4445")
    waitForSeleniumContainer(selenium_host, selenium_port, timeout=WAIT_SELENIUM_TIMEOUT)
    startScraping(selenium_host, selenium_port)



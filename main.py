
"""
Rental Property Data Entry Automation
-------------------------------------
1. Fetch rental listings from the sample website.
2. Extract and validate address, price, and listing URL.
3. Submit each valid listing to a Google Form.

Dependencies:
    pip install requests beautifulsoup4 selenium
"""

import logging
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ============================================================
# CONFIGURATION
# ============================================================

LISTINGS_URL = "https://appbrewery.github.io/Zillow-Clone/"

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScUcz3a1hjnqu194hrzIvkiKEh9TMPIsQDShJE2-_fU0gfAWg/"
    "viewform?usp=header"
)

REQUEST_TIMEOUT = 20
SELENIUM_TIMEOUT = 15

# Google Form field selectors from the original project.
ADDRESS_XPATH = (
    '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]'
    '/div/div/div[2]/div/div[1]/div/div[1]/input'
)

PRICE_XPATH = (
    '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]'
    '/div/div/div[2]/div/div[1]/div/div[1]/input'
)

LINK_XPATH = (
    '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]'
    '/div/div/div[2]/div/div[1]/div/div[1]/input'
)

SUBMIT_XPATH = (
    '//*[@id="mG61Hd"]/div[2]/div/div[3]/div[1]'
    '/div[1]/div/span/span'
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: FETCH THE WEBPAGE
# ============================================================

def fetch_listings_page():
    """Download the listings page and return its HTML."""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            LISTINGS_URL,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        logger.info("Listings webpage downloaded successfully.")
        return response.text

    except requests.RequestException as error:
        logger.error("Could not download listings: %s", error)
        return None


# ============================================================
# STEP 2: CLEAN AND EXTRACT DATA
# ============================================================

def clean_address(address):
    """Remove unwanted whitespace and separators from an address."""

    if not address:
        return ""

    return re.sub(r"\s+", " ", address).replace("|", "").strip()


def clean_price(price_text):
    """
    Extract a monthly rental price from text such as:
    '$2,500/mo', '$2,500+ 1 bd', or '$2,500'.
    """

    if not price_text:
        return ""

    match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", price_text)

    if not match:
        return ""

    return match.group(1).replace(",", "")


def scrape_listings(html):
    """Extract valid property records from individual listing cards."""

    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article")

    listings = []

    if not articles:
        logger.warning(
            "No listing cards found. The website structure may have changed."
        )
        return listings

    for article in articles:
        try:
            link_element = article.select_one("a[href]")
            address_element = article.select_one(
                ".StyledPropertyCardDataWrapper address"
            )

            # Find the price text within this property card only.
            price_text = ""

            for element in article.select("span"):
                text = element.get_text(" ", strip=True)

                if "$" in text:
                    price_text = text
                    break

            if not link_element or not address_element:
                logger.warning("Skipping a card with missing address or link.")
                continue

            address = clean_address(
                address_element.get_text(" ", strip=True)
            )

            price = clean_price(price_text)

            listing_url = urljoin(
                LISTINGS_URL,
                link_element.get("href", "").strip(),
            )

            if not address or not price or not listing_url:
                logger.warning(
                    "Skipping incomplete listing: %s", address or "Unknown"
                )
                continue

            if not listing_url.startswith(("https://", "http://")):
                logger.warning("Skipping invalid listing URL.")
                continue

            listings.append({
                "address": address,
                "price": price,
                "url": listing_url,
            })

        except (AttributeError, TypeError, ValueError) as error:
            logger.warning("Could not parse one listing: %s", error)

    # Avoid submitting the same URL more than once in this run.
    unique_listings = []
    seen_urls = set()

    for listing in listings:
        if listing["url"] not in seen_urls:
            seen_urls.add(listing["url"])
            unique_listings.append(listing)

    logger.info(
        "Extracted %s valid unique listings.", len(unique_listings)
    )

    return unique_listings


# ============================================================
# STEP 3: SUBMIT A LISTING TO GOOGLE FORMS
# ============================================================

def submit_listing(driver, listing):
    """Fill in and submit one listing. Return True if successful."""

    wait = WebDriverWait(driver, SELENIUM_TIMEOUT)

    try:
        driver.get(FORM_URL)

        address_field = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, ADDRESS_XPATH)
            )
        )

        price_field = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, PRICE_XPATH)
            )
        )

        link_field = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, LINK_XPATH)
            )
        )

        address_field.clear()
        address_field.send_keys(listing["address"])

        price_field.clear()
        price_field.send_keys(listing["price"])

        link_field.clear()
        link_field.send_keys(listing["url"])

        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, SUBMIT_XPATH)
            )
        )

        submit_button.click()

        # Confirm that Google Forms has accepted the response.
        wait.until(
            lambda current_driver: (
                "Your response has been recorded"
                in current_driver.page_source
                or "Submit another response"
                in current_driver.page_source
            )
        )

        logger.info(
            "Submitted successfully: %s", listing["address"]
        )
        return True

    except TimeoutException:
        logger.error(
            "Timed out while submitting: %s", listing["address"]
        )
        return False

    except WebDriverException as error:
        logger.error(
            "Browser error for %s: %s",
            listing["address"],
            error,
        )
        return False


# ============================================================
# STEP 4: RUN THE AUTOMATION
# ============================================================

def main():
    """Run the complete rental data-entry workflow."""

    html = fetch_listings_page()

    if html is None:
        logger.error("Stopping because the listings page was unavailable.")
        return 1

    listings = scrape_listings(html)

    if not listings:
        logger.error("No valid listings were found. Nothing was submitted.")
        return 1

    print(f"\nFound {len(listings)} valid rental listings.")

    # Preview a few records before opening the browser.
    for index, listing in enumerate(listings[:3], start=1):
        print(
            f"{index}. {listing['address']} | "
            f"${listing['price']} | {listing['url']}"
        )

    print(
        "\nThe program will submit these records to your configured "
        "Google Form."
    )

    driver = None
    successful = 0
    failed = 0

    try:
        driver = webdriver.Chrome()

        for index, listing in enumerate(listings, start=1):
            logger.info(
                "Processing listing %s of %s",
                index,
                len(listings),
            )

            if submit_listing(driver, listing):
                successful += 1
            else:
                failed += 1

    except WebDriverException as error:
        logger.error("Could not start or operate Chrome: %s", error)
        return 1

    finally:
        if driver is not None:
            driver.quit()

    print("\n========== SUMMARY ==========")
    print(f"Total listings: {len(listings)}")
    print(f"Successful submissions: {successful}")
    print(f"Failed submissions: {failed}")
    print("=============================")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

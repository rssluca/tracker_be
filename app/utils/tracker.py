import requests
from .notifications import send_slack_message
from ..models import AppTrackerChange
from ..constants import HEADERS, TRACKER_TYPES, TRACKER_METHODS


def get_xpath_new_item(id, url, params):
    from lxml import html

    page = requests.get(url, headers=HEADERS)

    if page.status_code != 200:
        send_slack_message(
            "ERROR!",
            f"ERROR {url} status code {page.status_code}",
            "TestAppBot",
            "#errors",
        )
        raise IOError(f"Call returned error {page.status_code}")
    else:
        tree = html.fromstring(page.content)

        title = tree.xpath(params["title_xpath"])
        # Check if the item containts info
        if len(title) == 0:
            raise ValueError(f"Tracker ID {id} returned no/incorrect data")

        title = title[0].text_content()
        item_url = tree.xpath(params["link_xpath"])[0].get("href")
        location = tree.xpath(params["location_xpath"])[0].text_content()

        return title, item_url, location


def get_selenium_new_item(id, url, params):
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--test-type")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        ChromeDriverManager().install(),
        options=options,
    )

    WebDriverWait(driver=driver, timeout=10).until(
        lambda x: x.execute_script("return document.readyState === 'complete'")
    )

    driver.get(url)

    title = driver.find_elements_by_xpath(params["title_xpath"])
    # Check if the item containts info
    if len(title) == 0:
        raise ValueError(f"Tracker ID {id} returned no/incorrect data")
    title = title[0].text

    item_url = driver.find_elements_by_xpath(params["link_xpath"])[0].get_attribute(
        "href"
    )
    location = driver.find_elements_by_xpath(params["location_xpath"])[0].text
    driver.close()
    return title, item_url, location


def run(
    id,
    name,
    search_key,
    site_name,
    site_url,
    tracker_url,
    login_user,
    login_pwd,
    tracker_type,
    tracker_method,
    params,
):

    if tracker_method == "xpath":
        title, item_url, location = get_xpath_new_item(id, tracker_url, params)
    else:
        title, item_url, location = get_selenium_new_item(id, tracker_url, params)

    # Also search word must be in the title since places like
    # Facebook marketplace list other stuff
    if search_key.lower() in title.lower():

        # If site url is not in item_url, prepend it
        if site_url not in item_url:
            item_url = site_url + item_url

        save = False
        if AppTrackerChange.objects.filter(tracker_id=id).exists():
            change = (
                AppTrackerChange.objects.filter(tracker_id=id)
                .order_by("id")
                .reverse()[0]
            )

            if change.item_url != item_url:
                save = True
        else:
            save = True

        if save:
            t = AppTrackerChange(tracker_id=id, item_desc=title, item_url=item_url)
            t.save()
            send_slack_message(
                f"New item from {name} search on {site_name}",
                f"{title} just become available in {location} - {item_url}",
                "TestAppBot",
                "#alert",
            )

import requests
import os
from .notifications import send_slack_message
from ..models import AppTrackerChange, AppSite
from ..constants import HEADERS, TRACKER_TYPES, TRACKER_METHODS


def get_selenium_driver():
    from selenium import webdriver

    if "EXECUTOR_URL" in os.environ and "SESSION_ID" in os.environ:
        try:
            driver = webdriver.Remote(
                command_executor=os.environ["EXECUTOR_URL"], desired_capabilities={}
            )
            driver.session_id = os.environ["SESSION_ID"]
            init_driver = False
        except:
            init_driver = True

    else:
        init_driver = True

    if init_driver:

        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import NoSuchElementException
        from webdriver_manager.chrome import ChromeDriverManager

        options = webdriver.ChromeOptions()

        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--test-type")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless")

        # Disable image loading
        chrome_prefs = {}
        options.experimental_options["prefs"] = chrome_prefs
        chrome_prefs["profile.default_content_settings"] = {"images": 2}
        chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}

        driver = webdriver.Chrome(
            ChromeDriverManager().install(),
            options=options,
        )

        WebDriverWait(driver=driver, timeout=10).until(
            lambda x: x.execute_script("return document.readyState === 'complete'")
        )

        driver.get("https://www.facebook.com")
        username = driver.find_element_by_id("email")
        password = driver.find_element_by_id("pass")
        submit = driver.find_element_by_name("login")
        username.send_keys(os.environ.get("FB_USER"))
        password.send_keys(os.environ.get("FB_PWD"))
        submit.click()

        os.environ["EXECUTOR_URL"] = driver.command_executor._url
        os.environ["SESSION_ID"] = driver.session_id

    return driver


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
    driver = get_selenium_driver()

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
    site_id,
    tracker_url,
    tracker_type,
    tracker_method,
    params,
):
    site = AppSite.objects.get(id=site_id)
    if tracker_method == "xpath":
        title, item_url, location = get_xpath_new_item(id, tracker_url, params)
    else:
        title, item_url, location = get_selenium_new_item(id, tracker_url, params)

    # Also search word must be in the title since places like
    # Facebook marketplace list other stuff
    if search_key.lower() in title.lower():

        # If site url is not in item_url, prepend it
        if site.url not in item_url:
            item_url = site.url + item_url

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
                f"New item from {name} search on {site.name}",
                f"{title} just become available in {location} - {item_url}",
                "TestAppBot",
                "#alert",
            )

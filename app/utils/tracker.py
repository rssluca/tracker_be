import requests
import os
from .notifications import send_slack_message
from ..models import AppTrackerChange, AppSite
from ..constants import HEADERS, TRACKER_TYPES, TRACKER_METHODS
from .selenium_driver import SeleniumDriver, is_fb_logged_in, fb_login
from lxml import html


def get_lxml_page(tracker_url):
    """Retrieve a page source with lxml html

    Args:
        tracker_url (string): The tracker url

    Raises:
        IOError: Page not 200/OK

    Returns:
        Object: lxml page tree
    """
    page = requests.get(tracker_url, headers=HEADERS)

    if page.status_code != 200:
        send_slack_message(
            "ERROR!",
            f"ERROR {tracker_url} status code {page.status_code}",
            "TestAppBot",
            "SLACK_KEY_ERROR_ALERTS",
        )
        raise IOError(f"Call returned error {page.status_code}")
    else:
        tree = html.fromstring(page.content)

        return tree


def get_selenium_page(tracker_url):
    """Retrieve a page source with Selenium

    Args:
        tracker_url (string): The tracker url

    Returns:
        list [object]: selenium_object and driver with page
    """
    try:
        selenium_object = SeleniumDriver()
        driver = selenium_object.driver

        if is_fb_logged_in(driver):
            print("Already logged in")
        else:
            print("Not logged in. Login")
            fb_login(driver, os.environ.get("FB_USER"), os.environ.get("FB_PWD"))

        driver.get(tracker_url)
        driver.implicitly_wait(5)
    except Exception as e:
        e_type = type(e).__name__
        print(e_type, "in Selenium get_page")

    return selenium_object, driver


def get_lxml_new_items(id, tracker_url, params):
    """Get new items from lxml tree and extract first title, location and link params from it
    TODO allow any params not just the above ones.

    Args:
        id (int): The id of the tracker
        tracker_url (string): The tracker url
        params (list[dict]): A list of xpaths (can change)

    Returns:
        list[string]: title, item_url, location
    """

    tree = get_lxml_page(tracker_url)

    title = item_url = location = None

    for set in params["xpaths"]:
        t = tree.xpath(set["title_xpath"])

        if len(t) != 0:
            title = t[0].text_content()
        if set["link_xpath"] != "":
            u = tree.xpath(set["link_xpath"])
            if len(t) != 0:
                item_url = u[0].get("href")
        if set["location_xpath"] != "":
            l = tree.xpath(set["location_xpath"])
            if len(l) != 0:
                location = l[0].text_content()

    return title, item_url, location


def get_selenium_new_items(id, tracker_url, params):
    """Get new items from the selenium page and extract first title, location and link params from it
    TODO allow any params not just the above ones.

    Args:
        id (int): The id of the tracker
        tracker_url (string): The tracker url
        params (list[dict]): A list of xpaths (can change)

    Returns:
        list[string]: title, item_url, location
    """
    selenium_object, driver = get_selenium_page(tracker_url)

    title = item_url = location = None

    for set in params["xpaths"]:
        t = driver.find_elements_by_xpath(set["title_xpath"])

        if len(t) != 0:
            title = t[0].text
        if set["link_xpath"] != "":
            u = driver.find_elements_by_xpath(set["link_xpath"])
            if len(t) != 0:
                item_url = u[0].get_attribute("href")
        if set["location_xpath"] != "":
            l = driver.find_elements_by_xpath(set["location_xpath"])
            if len(l) != 0:
                location = l[0].text

    selenium_object.quit()

    return title, item_url, location


def check_new_item(
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
        title, item_url, location = get_lxml_new_items(id, tracker_url, params)
    else:
        title, item_url, location = get_selenium_new_items(id, tracker_url, params)

    if title == None:
        send_slack_message(
            "ERROR!",
            f"ERROR Tracker ID {id} - {tracker_url} returned no/incorrect data {title, item_url, location}",
            "TestAppBot",
            "SLACK_KEY_ERROR_ALERTS",
        )
        raise ValueError(
            f"Tracker ID {id} returned no/incorrect data {title, item_url, location}"
        )

    # NOTE Move to facebook method
    if item_url and "?" in item_url:
        item_url = item_url.split("?")[0]

    # SKIP RULES
    skip = False
    # Also search word must be in the title since places like
    # Facebook marketplace list other stuff
    matches = ["wanted", "looking for", "anyone got"]
    if search_key.lower() not in title.lower() or any(
        x in title.lower() for x in matches
    ):
        skip = True

    save = False

    if not skip:
        # If site url is not in item_url, prepend it
        if site.url not in item_url:
            item_url = site.url + item_url

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
        token = (
            "SLACK_KEY_VESPA_ALERTS" if search_key == "vespa" else "SLACK_KEY_ALERTS"
        )
        send_slack_message(
            f"New item from {name} search on {site.name}",
            f"{title} just become available in {location} - {item_url}",
            "TestAppBot",
            token,
        )

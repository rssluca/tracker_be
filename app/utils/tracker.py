import requests
import os
from .notifications import send_slack_message
from ..models import AppTrackerChange, AppSite
from ..constants import HEADERS, TRACKER_TYPES, TRACKER_METHODS
from .selenium_driver import SeleniumDriver, is_fb_logged_in, fb_login


def get_xpaths(xpath_method, text_method_str, get_method_str, params, id, tracker_url):
    title = item_url = location = None

    for set in params["xpaths"]:
        t = xpath_method(set["title_xpath"])

        if len(t) != 0:
            title = getattr(t[0], text_method_str)()
        if set["link_xpath"] != "":
            u = xpath_method(set["link_xpath"])
            if len(t) != 0:
                item_url = getattr(u[0], get_method_str)("href")
        if set["location_xpath"] != "":
            l = xpath_method(set["location_xpath"])
            if len(l) != 0:
                location = getattr(l[0], text_method_str)()

    if title == None:
        send_slack_message(
            "ERROR!",
            f"ERROR Tracker ID {id} - {tracker_url} returned no/incorrect data {title, item_url, location}",
            "TestAppBot",
            "#general",
        )
        raise ValueError(
            f"Tracker ID {id} returned no/incorrect data {title, item_url, location}"
        )

    return title, item_url, location


def get_xpath_new_item(id, tracker_url, params):
    from lxml import html

    page = requests.get(tracker_url, headers=HEADERS)

    if page.status_code != 200:
        send_slack_message(
            "ERROR!",
            f"ERROR {tracker_url} status code {page.status_code}",
            "TestAppBot",
            "#errors",
        )
        raise IOError(f"Call returned error {page.status_code}")
    else:
        tree = html.fromstring(page.content)

    title, item_url, location = get_xpaths(
        tree.xpath, "text_content", "get", params, id, tracker_url
    )

    return title, item_url, location


def get_selenium_new_item(id, tracker_url, params):
    selenium_object = SeleniumDriver()
    driver = selenium_object.driver

    if is_fb_logged_in(driver):
        print("Already logged in")
    else:
        print("Not logged in. Login")
        fb_login(driver, os.environ.get("FB_USER"), os.environ.get("FB_PWD"))

    driver.get(tracker_url)
    driver.implicitly_wait(5)

    title = item_url = location = None

    title, item_url, location = get_xpaths(
        driver.find_elements_by_xpath, "text_content", "get", params, id, tracker_url
    )

    selenium_object.quit()

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

    if not skip:
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

from .models import Page, PageChange
import requests
from lxml import html
from .utils import send_slack_message

def check_page(page_id, url, xpath, available_tag):
    HEADERS = ({'User-Agent':
                'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
                'Accept-Language': 'en-US, en;q=0.5'})
    page = requests.get(url, headers=HEADERS)

    if page.status_code != 200:
        send_slack_message("ERROR!", f"ERROR {url} status code {page.status_code}", "TestAppBot", "#errors")
    else:
        tree = html.fromstring(page.content)

        try:
            content = str(html.tostring(tree.xpath(xpath)[0], pretty_print=True))
        except:
            content = ''

        is_available_now =  True if available_tag in content else False

        save = False
        # Check if any check exisit
        # If any, check last status
        if PageChange.objects.filter(page=page_id).exists():
            check = PageChange.objects.filter(page=page_id).order_by('page_change_id').reverse()[0]
            if check.is_available !=  is_available_now:
                # If available send a notification
                if is_available_now:
                    send_slack_message("AVAILABLE", f"{url} stock available!", "TestAppBot", "#alert")
                # Then trigger save
                save = True
        else:
            save = True

        if save:
            page = Page.objects.get(pk=page_id)
            p = PageChange(page=page, content=content, is_available=is_available_now)
            p.save()


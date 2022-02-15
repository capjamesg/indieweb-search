import datetime
import logging
from time import mktime

from . import constants
import feedparser
import indieweb_utils
import mf2py
import requests
from recrawling.recrawl_url import schedule_crawl_of_one_url


def process_xml_feed(url, feed_etag, site_url, f):
    feed = feedparser.parse(url)

    etag = feed.get("etag", "")

    if not feed:
        return url, etag, None

    if etag == feed_etag:
        logging.debug(f"{url} has not changed since last poll, skipping")
        return url, etag, None

    last_modified = feed.get("modified_parsed", None)

    if last_modified and datetime.datetime.fromtimestamp(
        mktime(last_modified)
    ) < datetime.datetime.now() - datetime.timedelta(hours=12):
        logging.debug(f"{url} has not been modified in the last 12 hours, skipping")
        return url, etag, None

    session = requests.Session()

    crawled = 0

    for entry in feed.entries:
        if entry.get("link"):
            url = indieweb_utils.canonicalize_url(entry.link, site_url)

            schedule_crawl_of_one_url(url, site_url, session)

            crawled += 1

    # close session
    session.close()

    # update etag
    f[2] = etag

    modify_feed = requests.post(
        "https://es-indieweb-search.jamesg.blog/update_feed",
        headers=constants.HEADERS,
        json={"item": f},
    )

    if modify_feed.status_code != 200:
        logging.debug(
            f"{modify_feed.status_code} status code returned while modifying {url}"
        )
    else:
        logging.debug(f"updated etag for {url}")

    return crawled


def process_h_feed(r, site_url):
    mf2_raw = mf2py.parse(r.text)

    session = requests.Session()

    crawled = 0

    for item in mf2_raw["items"]:
        if not item.get("type"):
            continue

        if item.get("type")[0] != "h-feed":
            continue

        if not item.get("children"):
            continue

        for child in item["children"]:
            url = indieweb_utils.canonicalize_url(
                child.get("properties").get("url")[0], site_url
            )

            schedule_crawl_of_one_url(url, site_url, session)

            crawled += 1

    # close session
    session.close()

    return crawled


def process_json_feed(r, site_url):
    # parse as JSON Feed per jsonfeed.org spec

    items = r.json().get("items")

    session = requests.Session()

    if not items or len(items) > 0:
        return

    crawled = 0

    for item in items:
        if not item.get("url"):
            continue

        schedule_crawl_of_one_url(item["url"], site_url, session)

        crawled += 1

    # close session
    session.close()

    return crawled


def renew_websub_hub_subscription(url, f):
    # send request to renew websub if the websub subscription has expired

    expire_date = f[3]

    if f[5] is False or datetime.datetime.now() > datetime.datetime.strptime(
        expire_date, "%Y-%m-%d"
    ):
        # random string of 20 letters and numbers
        # each websub endpoint needs to be different

        create_websub_subscription = requests.post(
            "https://es-indieweb-search.jamesg.blog/create_websub",
            headers=constants.HEADERS,
            data={"website_url": url},
        )

        requests.post(
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="hub.mode=subscribe&sub.topic={}&hub.callback=https://es-indieweb-search.jamesg.blog/websub/{}".format(
                url, create_websub_subscription.json()["key"]
            ),
        )

        logging.debug(f"sent websub request to {url}")


def poll_feeds(f, feeds_parsed):
    domain = f[0]
    url = indieweb_utils.canonicalize_url(f[1], domain)
    feed_etag = f[2]
    mime_type = f[4]

    # used to skip duplicate entries in feeds.txt
    if feeds_parsed.get(url.lower()):
        return

    feeds_parsed[url.lower()] = ""

    # request will return 304 if feed has not changed based on provided etag
    try:
        r = requests.get(url, headers={"If-None-Match": feed_etag.strip()}, timeout=10)
    except requests.exceptions.Timeout:
        logging.debug(f"timeout while requesting {url}")
        return 0

    # get etag
    etag = r.headers.get("etag")

    if r.status_code == 304:
        logging.debug(f"Feed {url} unchanged")
        return url, etag, None
    elif r.status_code != 200:
        logging.debug(f"{r.status_code} status code returned while retrieving {url}")
        return url, etag, None

    if r.headers.get("content-type"):
        content_type = r.headers["content-type"]
    else:
        content_type = ""

    logging.debug("polling " + url)

    allowed_xml_content_types = ["application/rss+xml", "application/atom+xml"]

    if (
        content_type in allowed_xml_content_types
        or mime_type in allowed_xml_content_types
        or mime_type == "feed"
    ):
        entries_in_feed_count = process_xml_feed(url, feed_etag, url, f)

    if mime_type == "h-feed":
        entries_in_feed_count = process_h_feed(r, url)

    elif mime_type == "application/json":
        entries_in_feed_count = process_json_feed(r, url)

    elif mime_type == "websub":
        renew_websub_hub_subscription(url, f)

        pass

    if etag is None:
        etag = ""

    return entries_in_feed_count

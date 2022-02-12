import concurrent.futures
import datetime
import logging
import os
from time import mktime

import feedparser
import mf2py
import microformats2
import requests
# ignore insecure request warning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import config
from crawler.verify_and_process import crawl_urls

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HEADERS = {
    "Authorization": config.ELASTICSEARCH_API_TOKEN,
    "Content-Type": "application/json",
}

# move results.json to a file with a datetime stamp
if os.path.isfile("results.json"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.rename("results.json", f"results-{now}.json")

feeds = requests.post(
    "https://es-indieweb-search.jamesg.blog/feeds", headers=HEADERS
).json()

feeds_parsed = {}


def poll_feeds(f):
    url = f[1]
    feed_etag = f[2]
    mime_type = f[4]

    # used to skip duplicate entries in feeds.txt
    if feeds_parsed.get(url.lower()):
        return

    feeds_parsed[url.lower()] = ""

    # request will return 304 if feed has not changed based on provided etag
    r = requests.get(url, headers={"If-None-Match": feed_etag.strip()})

    # get etag
    etag = r.headers.get("etag")

    if r.status_code == 304:
        print(f"Feed {url} unchanged")
        return url, etag, None
    elif r.status_code != 200:
        print(f"{r.status_code} status code returned while retrieving {url}")
        return url, etag, None

    if r.headers.get("content-type"):
        content_type = r.headers["content-type"]
    else:
        content_type = ""

    print("polling " + url)

    site_url = "https://" + url.split("/")[2]

    allowed_xml_content_types = ["application/rss+xml", "application/atom+xml"]

    if (
        content_type in allowed_xml_content_types
        or mime_type in allowed_xml_content_types
        or mime_type == "feed"
    ):
        feed = feedparser.parse(url)

        etag = feed.get("etag", "")

        if not feed:
            return url, etag, None

        if etag == feed_etag:
            print(f"{url} has not changed since last poll, skipping")
            return url, etag, None

        last_modified = feed.get("modified_parsed", None)

        if last_modified and datetime.datetime.fromtimestamp(
            mktime(last_modified)
        ) < datetime.datetime.now() - datetime.timedelta(hours=12):
            print(f"{url} has not been modified in the last 12 hours, skipping")
            return url, etag, None

        for entry in feed.entries:
            site_url = "https://" + entry.link.split("/")[2]
            session = requests.Session()

            if entry.get("link"):
                crawl_urls(
                    {entry.link: ""},
                    [],
                    0,
                    [],
                    [],
                    {},
                    [entry.link],
                    site_url,
                    1,
                    entry.link,
                    [],
                    [],
                    entry.link.split("/")[2],
                    session,
                    {},
                    [],
                    "",
                    False,
                    [],
                    0,
                )

            print(f"crawled {entry.link} url")

        # update etag
        f[2] = etag

        modify_feed = requests.post(
            "https://es-indieweb-search.jamesg.blog/update_feed",
            headers=HEADERS,
            json={"item": f},
        )

        if modify_feed.status_code != 200:
            print(
                f"{modify_feed.status_code} status code returned while modifying {url}"
            )
        else:
            print(f"updated etag for {url}")

    if mime_type == "h-feed":
        mf2_raw = mf2py.parse(r.text)

        for item in mf2_raw["items"]:
            if (
                item.get("type")
                and item.get("type")[0] == "h-feed"
                and item.get("children")
            ):
                for child in item["children"]:
                    jf2 = microformats2.to_jf2(child)
                    if jf2.get("url"):
                        if type(jf2["url"]) == list:
                            jf2["url"] = jf2["url"][0]

                        if jf2["url"].startswith("/"):
                            jf2["url"] = site_url + jf2["url"]

                        session = requests.Session()

                        crawl_urls(
                            {jf2["url"]: ""},
                            [],
                            0,
                            [],
                            [],
                            {},
                            [jf2["url"]],
                            site_url,
                            10,
                            jf2["url"],
                            feeds,
                            feed_url_list,
                            jf2["url"].split("/")[2],
                            session,
                            {},
                            [],
                            "",
                            False,
                            [],
                            0,
                        )

                        print(f"crawled {jf2['url']} url")

    elif mime_type == "application/json":
        # parse as JSON Feed per jsonfeed.org spec

        items = r.json().get("items")

        if items and len(items) > 0:
            for item in items:
                if item.get("url"):
                    session = requests.Session()
                    crawl_urls(
                        {item["url"]: ""},
                        [],
                        0,
                        [],
                        [],
                        {},
                        [item["url"]],
                        site_url,
                        10,
                        item["url"],
                        feeds,
                        feed_url_list,
                        item["url"].split("/")[2],
                        session,
                        {},
                        [],
                        "",
                        False,
                        [],
                        0,
                    )

                    print(f"crawled {item['url']} url")

    elif mime_type == "websub":
        # send request to renew websub if the websub subscription has expired

        expire_date = f[4]

        if f[5] is False or datetime.datetime.now() > datetime.datetime.strptime(
            expire_date, "%Y-%m-%dT%H:%M:%S.%fZ"
        ):
            # random string of 20 letters and numbers
            # each websub endpoint needs to be different

            headers = {"Authorization": config.ELASTICSEARCH_API_TOKEN}

            r = requests.post(
                "https://es-indieweb-search.jamesg.blog/create_websub",
                headers=headers,
                data={"website_url": url},
            )

            r = requests.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="hub.mode=subscribe&sub.topic={}&hub.callback=https://es-indieweb-search.jamesg.blog/websub/{}".format(
                    url, r.get_json()["key"]
                ),
            )

            print(f"sent websub request to {url}")

        pass

    if etag is None:
        etag = ""

    return url, etag, f


feeds_by_page = {}

for f in feeds:
    try:
        if feeds_by_page.get(f[1]):
            feeds_by_page[f[1]] = feeds_by_page[f[1]].append(f)
        else:
            feeds_by_page[f[1]] = [f]
    except Exception as e:
        print(e)
        continue

feed_url_list = []

for key, value in feeds_by_page.items():
    try:
        if value and len(value) > 1:
            print(value)
            to_add = [feed for feed in value if feed[4] == "h-feed"]
        elif value and len(value) < 2:
            to_add = value[0]

        feed_url_list.append(to_add)
    except Exception as e:
        print(e)
        continue

print(len(feed_url_list))


def process_feeds():
    feeds_indexed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(poll_feeds, item) for item in feeds]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                feeds_indexed += 1

                print(f"FEEDS INDEXED: {feeds_indexed}")
                logging.info(f"FEEDS INDEXED: {feeds_indexed}")

                try:
                    url, etag, full_item = future.result()

                    # feeds.append([url, etag])

                except Exception as e:
                    print(e)
                    pass

                futures.remove(future)


def process_crawl_queue_from_websub():
    r = requests.get(
        "https://es-indieweb-search.jamesg.blog/crawl_queue", headers=HEADERS
    )

    pages_indexed = 0

    to_crawl = r.json()

    domains_indexed = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [
            executor.submit(
                crawl_urls,
                {item: ""},
                [],
                0,
                [],
                [],
                {},
                [],
                "https://" + item,
                1,
                item,
                feeds,
                feed_url_list,
                False,
            )
            for item in to_crawl
        ]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                pages_indexed += 1

                print(f"PAGES INDEXED: {pages_indexed}")
                logging.info(f"PAGES INDEXED: {pages_indexed}")

                try:
                    domain = url_indexed.split("/")[2]

                    domains_indexed[domain] = domains_indexed.get(domain, 0) + 1

                    if domains_indexed[domain] > 50:
                        print(f"50 urls have been crawled on {domain}, skipping")
                        continue

                    url_indexed, discovered = future.result()

                    if url_indexed is None:
                        futures = []
                        break

                except Exception as e:
                    print(e)
                    pass

                futures.remove(future)


def process_sitemaps():
    r = requests.get("https://es-indieweb-search.jamesg.blog/sitemaps", headers=headers)

    pages_indexed = 0

    to_crawl = r.json()

    domains_indexed = {}

    sitemap_urls = []

    for item in to_crawl:
        sitemap_urls.append(item[0])

        domain = item[0].split("/")[2]

        domains_indexed[domain] = domains_indexed.get(domain, 0) + 1

        if domains_indexed[domain] > 50:
            print(f"50 urls have been crawled on {domain}, skipping")
            continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [
            executor.submit(
                crawl_urls,
                {item: ""},
                [],
                0,
                [],
                [],
                {},
                [],
                "https://" + item,
                1,
                item,
                feeds,
                feed_url_list,
                False,
            )
            for item in sitemap_urls
        ]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                pages_indexed += 1

                print(f"PAGES INDEXED: {pages_indexed}")
                logging.info(f"PAGES INDEXED: {pages_indexed}")

                try:
                    url_indexed, _ = future.result()

                    if url_indexed is None:
                        futures = []
                        break
                except Exception as e:
                    print(e)
                    pass

                futures.remove(future)


process_feeds()
# process_crawl_queue_from_websub()
# process_sitemaps()

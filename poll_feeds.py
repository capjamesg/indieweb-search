import requests
import mf2py
import datetime
import feedparser
import microformats2
from time import mktime
from crawler.url_handling import crawl_urls

# read feeds.txt
with open('feeds.txt', 'r') as f:
    feeds = f.readlines()

feeds_parsed = {}

for f in feeds:
    url, feed_etag = f.split(",")

    # used to skip duplicate entries in feeds.txt
    if feeds_parsed.get(url.lower()):
        continue

    feeds_parsed[url.lower()] = ""

    # request will return 304 if feed has not changed based on provided etag
    r = requests.get(url, headers={'If-None-Match': feed_etag.strip()})

    if r.status_code == 304:
        print("Feed {} unchanged".format(url))
        continue
    elif r.status_code != 200:
        print("{} status code returned while retrieving {}".format(r.status_code, url))
        continue

    if r.headers.get('content-type'):
        content_type = r.headers['content-type']
    else:
        content_type = ""

    print("polling " + url)

    if "xml" in content_type or ".xml" in url:
        feed = feedparser.parse(url)

        etag = feed.get("etag", "")

        if etag == feed_etag:
            print("{} has not changed since last poll, skipping".format(url))
            continue

        last_modified = feed.get("modified_parsed", None)

        if last_modified and datetime.datetime.fromtimestamp(mktime(last_modified)) < datetime.datetime.now() - datetime.timedelta(hours=12):
            print("{} has not been modified in the last 12 hours, skipping".format(url))
            continue

        for entry in feed.entries:
            site_url = "https://" + entry.link.split("/")[2]
            crawl_urls({entry.link: ""}, [], 0, [], [], {}, [], site_url, 1, entry.link, False, False)

            print("crawled {} url".format(entry.link))
    else:
        mf2_raw = mf2py.parse(r.text)

        for item in mf2_raw["items"]:
            if item.get("type") and item.get("type")[0] == "h-feed":
                for child in item["children"]:
                    jf2 = microformats2.to_jf2(child)
                    site_url = "https://" + jf2["url"].split("/")[2] 
                    crawl_urls([jf2["url"]], [], 0, [], [], {}, [], site_url, 1, jf2["url"], False, False)

                    print("crawled {} url".format(jf2["url"]))
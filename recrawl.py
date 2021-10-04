import requests
import mf2py
import csv
import datetime
import feedparser
import microformats2
from time import mktime
from crawler.url_handling import crawl_urls
import build_index
import concurrent.futures
import string
import random
import logging
import json
import config
import mysql.connector

# ignore insecure request warning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

database = mysql.connector.connect(
    host="localhost",
    user=config.MYSQL_DB_USER,
    password=config.MYSQL_DB_PASSWORD,
    database="feeds"
)

cursor = database.cursor()

feeds = cursor.execute("SELECT * FROM feeds").fetchall()

feeds_parsed = {}

def poll_feeds(f):
    url = f.get("url")
    feed_etag = f.get("etag")
    mime_type = f.get("mime_type")

    # used to skip duplicate entries in feeds.txt
    if feeds_parsed.get(url.lower()):
        return

    feeds_parsed[url.lower()] = ""

    # request will return 304 if feed has not changed based on provided etag
    r = requests.get(url, headers={'If-None-Match': feed_etag.strip()})

    # get etag
    etag = r.headers.get('etag')

    if r.status_code == 304:
        print("Feed {} unchanged".format(url))
        return
    elif r.status_code != 200:
        print("{} status code returned while retrieving {}".format(r.status_code, url))
        return

    if r.headers.get('content-type'):
        content_type = r.headers['content-type']
    else:
        content_type = ""

    print("polling " + url)

    site_url = "https://" + url.split("/")[2] 

    allowed_xml_content_types = ['application/rss+xml', 'application/atom+xml']

    if content_type in allowed_xml_content_types or mime_type in allowed_xml_content_types or mime_type == "feed":
        feed = feedparser.parse(url)

        etag = feed.get("etag", "")

        if etag == feed_etag:
            print("{} has not changed since last poll, skipping".format(url))
            return

        last_modified = feed.get("modified_parsed", None)

        if last_modified and datetime.datetime.fromtimestamp(mktime(last_modified)) < datetime.datetime.now() - datetime.timedelta(hours=12):
            print("{} has not been modified in the last 12 hours, skipping".format(url))
            return

        for entry in feed.entries:
            site_url = "https://" + entry.link.split("/")[2]
            crawl_urls({entry.link: ""}, [], 0, [], [], {}, [], site_url, 1, entry.link, False, feeds, feed_url_list, False)

            print("crawled {} url".format(entry.link))

        # update etag
        f["etag"] = etag
    elif mime_type == "h-feed":
        mf2_raw = mf2py.parse(r.text)

        for item in mf2_raw["items"]:
            if item.get("type") and item.get("type")[0] == "h-feed" and item.get("children"):
                for child in item["children"]:
                    jf2 = microformats2.to_jf2(child)
                    if jf2.get("url"):
                        if type(jf2["url"]) == list:
                            jf2["url"] = jf2["url"][0]
                        if jf2["url"].startswith("/"):
                            jf2["url"] = site_url + jf2["url"]

                        crawl_urls({jf2["url"]: ""}, [], 0, [], [], {}, [], site_url, 1, jf2["url"], False, feeds, feed_url_list, False)

                        print("crawled {} url".format(jf2["url"]))

    elif mime_type == "application/json":
        # parse as JSON Feed per jsonfeed.org spec

        items = r.json().get("items")

        if items and len(items) > 0:
            for item in items:
                if item.get("url"):
                    crawl_urls({item["url"]: ""}, [], 0, [], [], {}, [], "https://" + site_url, 1, item["url"], False, feeds, feed_url_list, False)

                    print("crawled {} url".format(item["url"]))

    elif mime_type == "websub":
        # send request to renew websub if the websub subscription has expired

        expire_date = f.get("expire_date")

        if f.get("websub_sent") != True or datetime.datetime.now() > datetime.datetime.strptime(expire_date, "%Y-%m-%dT%H:%M:%S.%fZ"):
            # random string of 20 letters and numbers
            # each websub endpoint needs to be different
            random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))

            with open("websub_subscriptions.txt", "a+") as file:
                file.write(url + "," + random_string + "\n")

            r = requests.post(url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data="hub.mode=subscribe&sub.topic={}&hub.callback=https://indieweb-search.jamesg.blog/websub/{}".format(url, random_string))

            print("sent websub request to {}".format(url))

        pass

    if etag == None:
        etag = ""
        
    return url, etag, f

feeds_indexed = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(poll_feeds, item) for item in feeds]
    
    while len(futures) > 0:
        for future in concurrent.futures.as_completed(futures):
            feeds_indexed += 1

            print("FEEDS INDEXED: {}".format(feeds_indexed))
            logging.info("FEEDS INDEXED: {}".format(feeds_indexed))
            
            try:
                url, etag, full_item = future.result()

                feeds.append([url, etag])

                if etag:
                    full_item["etag"] = etag

            except Exception as e:
                pass

            futures.remove(future)

# write feeds to feeds.json
with open("feeds.json", "w") as file:
    json.dump(feeds, file)

print("Checking sitemaps for new content")

to_crawl = []
domains_to_recrawl = []

with open("crawled.csv", "r") as f:
    reader = csv.reader(f)

    for item in reader:
        domain = item[0]
        date = item[1]

        domain = domain.strip().replace("\n", "")

        # read crawl_queue.txt
        try:
            crawl_budget, final_urls, namespaces_to_ignore = build_index.process_domain(domain, True)
        except:
            print("Error processing domain {}".format(domain))
            logging.info("Error processing domain {}".format(domain))
            continue

        # get todays date
        today = datetime.datetime.now()

        # get three weeks ago
        three_weeks_ago = today - datetime.timedelta(weeks=3)
        
        # if date is older than three weeks ago, add to to_crawl
        # if no date provided, also add to to_crawl
        for key, value in final_urls.items():
            if value and value != "":
                try:
                    # get item key string as datetime
                    item_date = datetime.datetime.strptime(value.split("T")[0], "%Y-%m-%d")

                    if item_date < three_weeks_ago:
                        to_crawl.append(key)
                except:
                    print("could not parse date for {}, skipping".format(item))
            elif not value:
                to_crawl.append(key)

pages_indexed = 0

# next_crawl_queue.txt contains all individual urls that should be crawled
# currently this file only contains urls found in websub
with open("next_crawl_queue.txt", "r") as f:
    for line in f:
        line = line.strip()

        if line not in to_crawl:
            to_crawl.append(line)

# this will remove all lines from next_crawl_queue.txt so we do not reindex the same urls in the next recrawl

file = open("next_crawl_queue.txt", "w+")

file.close()

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(crawl_urls, {item: ""}, [], 0, [], [], {}, [], "https://" + item, 1, item, feeds, feed_url_list, False) for item in to_crawl]
    
    while len(futures) > 0:
        for future in concurrent.futures.as_completed(futures):
            pages_indexed += 1

            print("PAGES INDEXED: {}".format(pages_indexed))
            logging.info("PAGES INDEXED: {}".format(pages_indexed))

            try:
                url_indexed, discovered = future.result()

                if url_indexed == None:
                    futures = []
                    break
            except Exception as e:
                print(e)
                pass

            futures.remove(future)
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
import logging
import config

# ignore insecure request warning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# read feeds.txt
with open('/home/james/crawler/feeds.txt', 'r') as f:
    feeds = f.readlines()
    feed_url_list = [x.split(",")[0].strip() for x in feeds]

feeds_parsed = {}

def poll_feeds(f):
    if len(f.split(", ")) > 1:
        url, feed_etag = f.split(",")
        url = "https://" + url
    else:
        url = "https://" + f.split()[0]
        feed_etag = ""

    # used to skip duplicate entries in feeds.txt
    if feeds_parsed.get(url.lower()):
        return

    feeds_parsed[url.lower()] = ""

    # request will return 304 if feed has not changed based on provided etag
    r = requests.get(url, headers={'If-None-Match': feed_etag.strip()})

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

    if "xml" in content_type or ".xml" in url:
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
            crawl_urls({entry.link: ""}, [], 0, [], [], {}, [], site_url, 1, entry.link, False, feed_url_list, False)

            print("crawled {} url".format(entry.link))
    else:
        mf2_raw = mf2py.parse(r.text)

        for item in mf2_raw["items"]:
            if item.get("type") and item.get("type")[0] == "h-feed" and item.get("children"):
                for child in item["children"]:
                    jf2 = microformats2.to_jf2(child)
                    site_url = "https://" + url.split("/")[2] 
                    if jf2.get("url"):
                        if type(jf2["url"]) == list:
                            jf2["url"] = jf2["url"][0]
                        if jf2["url"].startswith("/"):
                            jf2["url"] = site_url + jf2["url"]

                        crawl_urls({jf2["url"]: ""}, [], 0, [], [], {}, [], site_url, 1, jf2["url"], False, feed_url_list, False)

                        print("crawled {} url".format(jf2["url"]))

feeds_indexed = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
	futures = [executor.submit(poll_feeds, item) for item in feeds]
	
	while len(futures) > 0:
		for future in concurrent.futures.as_completed(futures):
			feeds_indexed += 1

			print("FEEDS INDEXED: {}".format(feeds_indexed))
			logging.info("FEEDS INDEXED: {}".format(feeds_indexed))

			try:
				url_indexed, discovered = future.result()

				if url_indexed == None:
					futures = []
					break
			except Exception as e:
				pass

			futures.remove(future)

print("Checking sitemaps for new content")

to_crawl = []
domains_to_recrawl = []

with open("/home/james/crawler/crawled.csv", "r") as f:
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

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(crawl_urls, {item: ""}, [], 0, [], [], {}, [], "https://" + item, 1, item, False, feed_url_list, False) for item in to_crawl]
    
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
                pass

            futures.remove(future)
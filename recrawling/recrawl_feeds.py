import concurrent.futures
import datetime
import logging
import os

import constants
import feed_polling
import requests
# ignore insecure request warning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(
    filename=f"logs/recrawl/{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# move results.json to a file with a datetime stamp
if os.path.isfile("results.json"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.rename("results.json", f"results-{now}.json")

feeds = requests.post(
    "https://es-indieweb-search.jamesg.blog/feeds", headers=constants.HEADERS
).json()

feeds_parsed = {}


def prepare_feeds_for_polling():
    feeds_by_page = {}

    for f in feeds:
        try:
            if feeds_by_page.get(f[1]):
                feeds_by_page[f[1]] = feeds_by_page[f[1]].append(f)
            else:
                feeds_by_page[f[1]] = [f]
        except Exception as e:
            logging.debug(e)
            continue

    feed_url_list = []

    for value in feeds_by_page.values():
        try:
            if value and len(value) > 1:
                logging.debug(value)
                to_add = [feed for feed in value if feed[4] == "h-feed"]
            elif value and len(value) < 2:
                to_add = value[0]

            feed_url_list.append(to_add)
        except Exception as e:
            logging.debug(e)
            continue

    return feed_url_list


def process_feeds(feeds):
    feeds_indexed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(feed_polling.poll_feeds, item) for item in feeds]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                feeds_indexed += 1

                logging.debug(f"FEEDS INDEXED: {feeds_indexed}")
                logging.info(f"FEEDS INDEXED: {feeds_indexed}")

                try:
                    future.result()
                except Exception as e:
                    logging.debug(e)
                    pass

                futures.remove(future)


feed_url_list = prepare_feeds_for_polling()

process_feeds(feeds)

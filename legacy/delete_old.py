import csv
import json

from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from requests.api import request

es = Elasticsearch(["http://localhost:9200"])

# Function from https://simplernerd.com/elasticsearch-scroll-python/
# All credit to them for the function
def scroll(es, index, body, scroll, size, **kw):
    page = es.search(index=index, body=body, scroll=scroll, size=size, **kw)
    scroll_id = page["_scroll_id"]
    hits = page["hits"]["hits"]
    while len(hits):
        yield hits
        page = es.scroll(scroll_id=scroll_id, scroll=scroll)
        scroll_id = page["_scroll_id"]
        hits = page["hits"]["hits"]


body = {"query": {"match_all": {}}}

count = 0

domain_links = {}

link_microformat_instances = {}

# Get all links on each page in the index
# Write all links to a file

overall_count = 0

import requests

urls = []

# with open('links.csv', 'w+') as f:
for hits in scroll(es, "pages", body, "3m", 40):
    # overall_count += 1

    # if overall_count == 10:
    #     break

    for h in hits:
        # don't count links on pages that specified nofollow in the X-Robots-Tag header
        # if h["_source"].get("page_is_nofollow") and h["_source"].get("page_is_nofollow") == "true":
        #     continue

        urls.append(h["_source"]["url"])

import concurrent.futures

import config

print("created list of urls")
print("moving on to deletion stage")


def verify(url):
    try:
        r = requests.get(
            url, headers=config.HEADERS, allow_redirects=True, verify=False
        )
    except:
        es.delete(index="pages", id=h["_id"])

        print("deleted {}".format(url))

    if r.status_code == 404 or r.status_code == 410 or r.status_code == 500:
        es.delete(index="pages", id=h["_id"])

        print("deleted {}".format(url))


with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(verify, url) for url in urls]

    for f in concurrent.futures.as_completed(futures):
        pass

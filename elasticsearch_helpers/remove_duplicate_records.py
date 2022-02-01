import csv
import json

from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

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

all_urls = {}
to_remove = []

# First for loop to get all links from https://simplernerd.com/elasticsearch-scroll-python/
# Get all links on each page in the index
# Write all links to a file
for hits in scroll(es, "pages", body, "2m", 20):
    for hit in hits:
        url = hit["_source"]["url"].strip("/")
        if all_urls.get(url):
            to_remove.append(hit["_id"])
        else:
            all_urls[url] = hit["_id"]

        count += 1
        print(count)

for hit in to_remove:
    es.delete(index="pages", id=hit)

print("done")

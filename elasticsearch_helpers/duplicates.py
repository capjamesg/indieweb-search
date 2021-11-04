from elasticsearch import Elasticsearch
from bs4 import BeautifulSoup
import csv
import json

es = Elasticsearch(['http://localhost:9200'])

# Function from https://simplernerd.com/elasticsearch-scroll-python/
# All credit to them for the function
def scroll(es, index, body, scroll, size, **kw):
    page = es.search(index=index, body=body, scroll=scroll, size=size, **kw)
    scroll_id = page['_scroll_id']
    hits = page['hits']['hits']
    while len(hits):
        yield hits
        page = es.scroll(scroll_id=scroll_id, scroll=scroll)
        scroll_id = page['_scroll_id']
        hits = page['hits']['hits']

body = {"query": {"match_all": {}}} 

count = 0

links = {}

# First for loop to get all links from https://simplernerd.com/elasticsearch-scroll-python/
# Get all links on each page in the index
# Write all links to a file
for hits in scroll(es, 'pages', body, '2m', 20):
    for h in hits:
        # replacing www. for consistency
        print(count)
        if links.get(h['_source']['url'].replace("www.", "").lower().strip("/")) == None:
            links[h['_source']['url'].replace("www.", "").lower().strip("/")] = h['_id']
        else:
            es.delete(index='pages', id=h['_id'])
            count += 1
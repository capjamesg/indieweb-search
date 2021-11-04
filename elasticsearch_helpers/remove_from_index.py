from elasticsearch import Elasticsearch
from .scroll import scroll

es = Elasticsearch(['http://localhost:9200'])

body = {"query": {"match_all": {}}} 

count = 0

domain_links = {}

remove_domains = []

# Remove domains
for hits in scroll(es, 'pages', body, '2m', 20):
    for hit in hits:
        if hit["_source"]["domain"] in remove_domains:
            es.delete(index='pages', id=hit["_id"])
            count += 1

print("records removed: " + str(count))
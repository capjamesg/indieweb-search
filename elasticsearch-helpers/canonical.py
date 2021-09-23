from elasticsearch import Elasticsearch
from bs4 import BeautifulSoup
from scroll import scroll

es = Elasticsearch(['http://localhost:9200'])

body = {"query": {"match_all": {}}} 

count = 0

# Remove domains
for hits in scroll(es, 'pages', body, '2m', 20):
    for hit in hits:
        soup = BeautifulSoup(hit['_source']['page_content'], 'html.parser')

        for link in soup.find_all('link', rel='canonical'):
            canonical = link.get("href")
            if canonical and canonical.startswith("/"):
                canonical = "https://" + hit['_source']['domain'] + canonical
                
            if canonical and canonical.strip("/").replace("http://", "https://").split("?")[0] != hit['_source']['url'].strip("/").replace("http://", "https://").split("?")[0]:
                print(hit['_source']['page_url'], canonical)
                # es.delete(index='pages', doc_type='page', id=hit['_id'])
                count += 1

print("records removed: " + str(count))
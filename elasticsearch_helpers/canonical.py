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

        is_canonical = False

        if len(soup.find_all('link', rel='canonical')) == 0:
            continue

        for link in soup.find_all('link', rel='canonical'):
            canonical = link.get("href")

            if canonical and canonical.startswith("/"):
                canonical = "https://" + hit['_source']['domain'] + canonical
                
            if canonical and canonical.strip("/").replace("http://", "https://").split("?")[0] == hit['_source']['url'].strip("/").replace("http://", "https://").split("?")[0]:
                is_canonical = True

        if is_canonical == False:
            # es.delete(index='pages', id=hit['_id'])
            print(count)
            print(hit['_source']['url'])
            count += 1

print("records removed: " + str(count))
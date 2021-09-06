from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, helpers
import sqlite3

es = Elasticsearch(['http://localhost:9200'])

response = es.search(index="pages", body={"query":{"match_all":{}}}, size=1000, scroll="2s")

pages = []
iter = 0

scroll_size = len(response['hits']['hits'])

while scroll_size > 0:
    response = es.scroll(scroll_id=response['_scroll_id'], scroll="2s")

    scroll_size = len(response['hits']['hits'])

    if iter < 25:
        pages.extend(response['hits']['hits'])
    else:
        scroll_size = 0

    iter+=1
    print(iter)

# domains = set()

# for p in pages:
#     domain = p['_source']['url'].split('/')[2]
#     domains.add(domain)

# # write domains to file
# with open('domains.txt', 'a') as f:
#     for d in domains:
#         f.write(d + '\n')

for p in pages:
    page_html = p['_source']['page_content']

    soup = BeautifulSoup(page_html, 'html.parser')

    page_text = soup.get_text()

    # make text unicode
    page_text = page_text.encode('utf-8').decode('utf-8').replace("\n", " ")

    es.update(index="pages", id=p['_id'], body={"doc":{"text":page_text}})
from elasticsearch import Elasticsearch
from bs4 import BeautifulSoup

es = Elasticsearch(['http://localhost:9200'])

response = es.search(index="pages", body={"query":{"match_all":{}}}, size=1000, scroll="2s")

pages = []
iter = 0

scroll_size = len(response['hits']['hits'])

while scroll_size > 0:
    response = es.scroll(scroll_id=response['_scroll_id'], scroll="2s")

    scroll_size = len(response['hits']['hits'])

    if iter > 25:
        pages.extend(response['hits']['hits'])

    if iter > 50:
        break

    iter+=1
    print(iter)

for page in pages:
    # if url startswith indieweb and meta description contains "stub"
    if page['_source']['url'].startswith('https://indieweb.org/') and "stub" in page['_source']['description']:
        soup = BeautifulSoup(page['_source']["page_content"], "lxml")
        # get p tag after stub
        stub = [p for p in soup.find_all('p') if "stub" in p.get_text()][0]

        # get element after stub
        new_meta_description = " ".join(stub.find_next_sibling().get_text().split(" ")[:50])
        
        if len(stub.find_next_sibling().get_text().split(" ")) > 50:
            new_meta_description += "..."

        # update meta desc
        es.update(index="pages", id=page['_id'], body={"doc":{"description":new_meta_description}})
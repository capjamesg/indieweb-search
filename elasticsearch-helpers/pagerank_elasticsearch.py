from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])

from bs4 import BeautifulSoup
import networkx as nx
import tldextract
import json

indexed = {}
incoming = {}
domains = {}
page_id = {}

G = nx.DiGraph(nx.path_graph(4))

# get all domains in pages elasticsearch
response = es.search(index="pages", body={"query":{"match_all":{}}}, size=1000, scroll="2s")

pages = []
iter = 0

scroll_size = len(response['hits']['hits'])

while scroll_size > 0:
    response = es.scroll(scroll_id=response['_scroll_id'], scroll="2s")

    scroll_size = len(response['hits']['hits'])

    if iter > 25:
        pages.extend(response['hits']['hits'])

    iter+=1
    print(iter)

print('processing links')

# get all pages in domain with elasticsarch

total_all_links = {}

for page in pages:
    page_desc_soup = BeautifulSoup(page["_source"]["page_content"], 'lxml')
    
    # G.add_node(page["_source"]["url"])

    page_id[page["_source"]["url"]] = page["_id"]

    all_links = page_desc_soup.find_all('a')

    domain = page["_source"]["url"].split("//")[-1].split("/")[0]

    for link in all_links:
        if link.get("href"):
            if link["href"].startswith("/"):
                link["href"] = "https://" + domain + link["href"]

            if total_all_links.get(link["href"]):
                total_all_links[link["href"]] = total_all_links[link["href"]] + 1
            else:
                total_all_links[link["href"]] = 1
            # try:
            #     G.add_node(link["href"])
            #     G.add_edge(link["href"], page["_source"]["url"])
            # except:
            #     pass

print('calculating pagerank')

# pr = nx.pagerank(G, alpha=0.9, max_iter=100, tol=1e-06)

print('calculated pagerank')

failed = 0
tried = 0

# save pr.items() to file
with open("pagerank_elasticsearch.json", "w+") as f:
    f.write(json.dumps(total_all_links))

print('saved pagerank to file')

# for url, value in pr.items():
#     tried +=1
#     if page_id.get(url):
#         try:
#             print(url, value)
#             es.update("pages", page_id.get(url), body={"doc": { "pagerank": value }})
#         except Exception as e:
#             failed +=1
#             print(e)

# print("tried {}, failed {}".format(tried, failed))
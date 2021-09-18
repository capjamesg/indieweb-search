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

# First for loop to get all links from https://simplernerd.com/elasticsearch-scroll-python/
# Get all links on each page in the index
# Write all links to a file
for hits in scroll(es, 'pages', body, '2m', 20):
    for h in hits:
        soup = BeautifulSoup(h['_source']['page_content'], 'html.parser')

        links = soup.find_all('a')

        print(count)
        print(h["_source"]["url"])
        count += 1

        domain = h["_source"]["url"].split('/')[2]

        with open('links.csv', 'a') as f:
            for l in links:
                if l.has_attr('href'):
                    if l["href"].startswith("/"):
                        link = "https://" + h["_source"]["domain"] + l.get('href')
                    elif l["href"].startswith("//"):
                        link = "https:" + l.get('href')
                    else:
                        link = l.get('href')

                link_domain = l.get('href').split('/')[2]

                if domain == link_domain: 
                    points = 1
                elif "u-in-reply-to" in l.get("class") and domain != link_domain:
                    points = 5
                elif ("u-repost-of" in l.get("class") or "u-quotation-of" in l.get("class")) and domain != link_domain:
                    points = 4
                elif "u-bookmark-of" in l.get("class") and domain != link_domain:
                    points = 3
                elif "u-like-of" in l.get("class") and domain != link_domain:
                    points = 2
                else:
                    points = 1

                # points go to the link
                csv.writer(f).writerow([h["_source"]["url"], link, points])

links = {}
count = 0

# Open links file
# Create dictionary with the number of times each domain appears
for line in open("links.csv"):
    line = line.strip()

    link = line.split(",")

    # get domain of link
    try:
        domain_1 = link[0].split("//")[1].split("/")[0]
        domain_2 = link[1].split("//")[1].split("/")[0]
        if domain_1 != domain_2:
            if links.get(link[1]):
                links[link[1]] = links[link[1]] + 1
            else:
                links[link[1]] = 1
        count += 1
        print(count)
    except:
        print("error with link")

# write links to all_links_final.json
with open('all_links_final.json', 'w+') as f:
    json.dump(links, f)

with open('all_links_final.json', 'r') as f:
    links = json.load(f)

count = 0 

# update incoming_links attribute
for link, link_count in links.items():
    search_param = {
        "query": {
            "term": {
                "url.keyword": {
                    "value": link
                }
            }
        }
    }

    response = es.search(index="pages", body=search_param)

    if len(response["hits"]["hits"]) == 0:
        print("No results for " + link)
    else:
        es.update(index="pages", id=response['hits']['hits'][0]['_id'], body={"doc": {"incoming_links": link_count}})

        full_link = response['hits']['hits'][0]['_source']['url']

        print(full_link)

        count += 1
        print(count)
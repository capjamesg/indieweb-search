import json

from elasticsearch import Elasticsearch

es = Elasticsearch(["http://localhost:9200"])

# read pagerank_elasticsearch.json
with open("pagerank_elasticsearch.json", "r") as f:
    pagerank_elasticsearch = json.load(f)

with open("pagerank_elasticsearch_1.json", "r") as f:
    pagerank_elasticsearch_1 = json.load(f)

# merge dicts
pagerank_elasticsearch.update(pagerank_elasticsearch_1)

tried = 0
failed = 0

for url, value in pagerank_elasticsearch.items():
    tried += 1
    try:
        # get elasticsearch id where url = url
        res = es.search(index="pages", body={"query": {"match": {"url": url}}})
        id = res["hits"]["hits"][0]["_id"]
        if res and id:
            es.update("pages", id, body={"doc": {"incoming_links": value}})
            print(url)
    except Exception as e:
        failed += 1
        print(e)

print(f"tried {tried}, failed {failed}")

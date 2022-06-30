import json

import requests
from elasticsearch import Elasticsearch

import config

es = Elasticsearch("http://localhost:9200")

objects = []

valid = 0

print("starting")

def get_first_crawled_date(new_record: dict, index_item: dict):
    index_item = index_item[0]

    if index_item.get("first_crawled"):
        return index_item["first_crawled"]
    elif index_item.get("last_crawled"):
        return index_item.get("last_crawled")
    else:
        return new_record["last_crawled"]
    

# open results.json
with open("results.json") as f:
    for l in range(0, 1):
        line = f.readline()
        try:
            obj = json.loads(line)

            check_if_indexed = requests.post(
                f"https://es-indieweb-search.jamesg.blog/check?url={obj['url']}",
                headers={"Authorization": f"Bearer {config.ELASTICSEARCH_API_TOKEN}"},
                timeout=5,
            ).json()

            if len(check_if_indexed) == 0:
                es.index(index="pages", body=obj)
            else:
                # incoming_links is set to 0 by default
                # delete incoming_links value so the calculated incoming links value is not overwritten
                del obj["incoming_links"]
                # get item from es

                obj["first_crawled"] = get_first_crawled_date(obj, check_if_indexed)

                es.update(
                    index="pages", id=check_if_indexed[0]["_id"], body={"doc": obj}
                )

            valid += 1
            print(valid)
        except:
            continue

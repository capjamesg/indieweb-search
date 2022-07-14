import json

import requests
from elasticsearch import Elasticsearch

import config

es = Elasticsearch("http://localhost:9200")

import datetime

from influxdb import InfluxDBClient

client = InfluxDBClient(host="localhost", port=8086)

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
    for l in range(0, 1000):
        line = f.readline()
        print(json.loads(line))
        try:
            obj = json.loads(line)

            check_if_indexed = requests.get(
                f"https://es-indieweb-search.jamesg.blog/check?url={obj['url']}",
                headers={"Authorization": f"Bearer {config.ELASTICSEARCH_API_TOKEN}"},
                timeout=5,
            )

            if check_if_indexed.status_code != 200 or len(check_if_indexed.json()) == 0:
                es.index(index="pages", body=obj)

                domain = obj["url"].split("/")[2]

                data = [
                    {
                        "measurement": "crawl",
                        "time": datetime.datetime.utcnow().isoformat(),
                        "fields": {
                            "text": f"[*{domain}*] [INDEXER] {obj['url']} has been saved in the index for the first time"
                        },
                    }
                ]

                client.write_points(data, database="search_logs")
            else:
                # incoming_links is set to 0 by default
                # delete incoming_links value so the calculated incoming links value is not overwritten
                del obj["incoming_links"]
                # get item from es

                obj["first_crawled"] = get_first_crawled_date(obj, check_if_indexed)

                es.update(
                    index="pages", id=check_if_indexed[0]["_id"], body={"doc": obj}
                )
                data = [
                    {
                        "measurement": "crawl",
                        "time": datetime.datetime.utcnow().isoformat(),
                        "fields": {
                            "text": f"[*{domain}*] [INDEXER] {obj['url']} has been updated in the index"
                        },
                    }
                ]

                client.write_points(data, database="search_logs")

            valid += 1
            print(valid)
        except Exception as e:
            print(e)

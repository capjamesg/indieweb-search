import json
import requests
import config
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

objects = []

valid = 0

print("starting")

# open results.json
with open('results.json') as f:
    for l in range(0, 226621):
        line = f.readline()
        try:
            obj = json.loads(line)
            
            if "tools.ietf.org" in obj["domain"] or  "linkedin.com" in obj["domain"] or "wireshell.pw" in obj["domain"] or "pixelhunter.me" in obj["domain"] or "getpop.org" in obj["domain"] or "github.com" in obj["domain"] or "codemonkey.withknown.com" in obj["domain"] or "/opensource/opensource/opensource/" in obj["domain"]:
                continue

            check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(obj["url"]), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, timeout=5).json()

            if len(check_if_indexed) == 0:
                es.index(index="pages", body=obj)
            else:
                # incoming_links is set to 0 by default
                # delete incoming_links value so the calculated incoming links value is not overwritten
                del obj["incoming_links"]
                es.update(index="pages", id=check_if_indexed[0]["_id"], body={"doc": obj})

            valid += 1
            print(valid)
        except:
            continue
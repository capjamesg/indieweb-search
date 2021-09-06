from flask import Flask, request, abort, jsonify, send_from_directory
from elasticsearch import Elasticsearch
import random
from . import config

es = Elasticsearch(['http://localhost:9200'])

app = Flask(__name__)

@app.route("/")
def home():
    pw = config.ELASTICSEARCH_PASSWORD
    query = request.args.get("q")
    domain_param = request.args.get("domain")
    from_num = request.args.get("from")
    if not from_num:
        from_num = 1
    to_num = request.args.get("to")
    if not to_num:
        to_num = 10

    if request.args.get("pw") != pw:
        return abort(401)

    site = request.args.get("site")

    query = query.replace("what is ", "").replace("who is ", "")

    query = query.strip().replace(" ", " AND ")

    if site and len(site) > 0:
        query = query + " AND (url:{})".format(site)
    elif site and len(site) == 0:
        query = "(url:{})".format(site)

    inurl = request.args.get("inurl")

    if inurl and len(inurl) > 0:
        query = query + " AND (url:{})".format(inurl)
    elif inurl and len(inurl) == 0:
        query = "(url:{})".format(inurl)

    search_param = {
        "from": int(from_num),
            "size": int(from_num) + 10,
        "query": {
            "script_score": {
                "query": {
                    "query_string": {
                        "query": query,
                        "fields": ["title^5", "description^3", "url^3", "category^0", "published^0", "keywords^0", "text^3", "h1^5", "h2^1.5", "h3^1.2", "h4^0.5", "h5^0.75", "h6^0.25"],
                        "minimum_should_match": "3<90%"
                    },
                },
                "script": {
                    "source": "_score" 
                }
        }
    }}
    
    # + (doc['incoming_links'].value / 100)

    if domain_param:
        domain = query.replace("who is ", "")

        # get domain homepage
        search_param = {
            "from": 0,
            "size": 1,
            "query": {
                "match": {
                    "url": "https://" + domain.strip()
                }
            }
        }

    #* saturation(doc['pagerank'].value, 10)"

    response = es.search(index="pages", body=search_param)

    return response

@app.route("/create", methods=["POST"])
def create():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        data = request.get_json()

        es.index(index="pages", doc_type="page", body=data)

        return jsonify({"status": "ok"})
    else:
        return abort(401)

@app.route("/update", methods=["POST"])
def update():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        data = request.get_json()

        # get document with same url as data['url']
        search_param = {
            "query": {
                "match": {
                    "url": data['url']
                }
            }
        }

        response = es.search(index="pages", body=search_param)

        es.update(index="pages", id=response[0]["_id"], body=data)

        return jsonify({"status": "ok"})
    else:
        return abort(401)

@app.route("/check", methods=["POST"])
def check():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        hash = request.args.get("hash")

        # get document with same hash as hash arg
        search_param = {
            "query": {
                "match": {
                    "md5hash": hash
                }
            }
        }

        response = es.search(index="pages", body=search_param)

        if response:
            return response
        else:
            return jsonify({"status": "not found"})
    else:
        return abort(401)

@app.route("/count")
def show_num_of_pages():
    count = es.count(index="pages")

    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    return jsonify({"es_count": count, "domains": len(domains)})

@app.route("/random")
def random_page():
    if request.args.get("pw") != config.ELASTICSEARCH_PASSWORD:
        return abort(401)
        
    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    # get random domain
    domain = domains[random.randint(0, len(domains) - 1)].strip()

    return jsonify({"domain": domain})

@app.route("/assets/<path:path>")
def send_assets(path):
    return send_from_directory("assets", path)
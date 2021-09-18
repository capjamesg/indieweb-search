from flask import Flask, request, abort, jsonify, send_from_directory
from elasticsearch import Elasticsearch, helpers
import random
import config

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

    if request.args.get("pw") != pw:
        return abort(401)

    site = request.args.get("site")

    query = query.replace("what is ", "").replace("who is ", "")

    query = query.strip().replace(" ", " AND ")

    final_query = ""

    if len(query) > 0:
        for w in range(0, len(query.split(" "))):
            if w == 0:
                final_query += query.split(" ")[w] + "^3"
            else:
                final_query += query.split(" ")[w]

        if site and len(site) > 0:
            query = query + " AND (url:{})".format(site)
        elif site and len(site) == 0:
            query = "(url:{})".format(site)

        inurl = request.args.get("inurl")

        if inurl and len(inurl) > 0:
            query = query + " AND (url:{})".format(inurl)
        elif inurl and len(inurl) == 0:
            query = "(url:{})".format(inurl)
    else:
        if site and len(site) > 0:
            query = query + "(url:{})".format(site)
        elif site and len(site) == 0:
            query = "(url:{})".format(site)

        inurl = request.args.get("inurl")

        if inurl and len(inurl) > 0:
            query = query + "(url:{})".format(inurl)
        elif inurl and len(inurl) == 0:
            query = "(url:{})".format(inurl)

    search_param = {
        "from": int(from_num),
        "size": 10,
        # use script to calculate score
        "query": {
            "script_score": {
                "query": {
                    "query_string": {
                        "query": query,
                        "fields": ["title^2", "description^1", "url^1.5", "category^0", "published^0", "keywords^0", "text^3", "h1^2", "h2^1.5", "h3^1.2", "h4^0.5", "h5^0.75", "h6^0.25"],
                        "minimum_should_match": "3<75%",
                    },
                },
                "script": {
                    "source": """return _score + Math.log((1 + (doc['word_count'].value))) + Math.sqrt((1 + (doc['incoming_links'].value)) * 5);
                    """
                },
            },
        },
        "highlight": {
            "pre_tags": ["<b>"],
            "post_tags": ["</b>"],
            "fields": {
                "description": {},
            },
        },
    }
    
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

@app.route("/create-bulk", methods=["POST"])
def create_bulk():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        data = request.get_json()

        res = helpers.bulk(es, data)

        print(res)

        return jsonify({"status": "ok"})
    else:
        return abort(401)

@app.route("/remove-from-index", methods=["POST"])
def remove_from_index():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        data = request.get_json()

        # remove from elasticsearch
        res = es.delete(index="pages", doc_type="page", id=data["id"])

        return jsonify({"status": "ok"})
    else:
        return abort(401)

@app.route("/create", methods=["POST"])
def create():
    if request.method == "POST":
        # check auth header
        if request.headers.get("Authorization") != "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN):
            return abort(401)

        data = request.get_json()

        total_docs_today = int(es.count(index='pages')['count'])

        i = es.index(index="pages", body=data, id=total_docs_today + 1)

        print(i)

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

        es.update(index="pages", id=response["hits"]["hits"][0]["_id"], body={"doc":data})

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

        if hash:
            # get document with same hash as hash arg
            search_param = {
                "query": {
                    "match": {
                        "md5hash": hash
                    }
                }
            }
        else:
            search_param = {
                "query": {
                    "term": {
                        "url.keyword": {
                            "value": request.args.get("url")
                        }
                    }
                }
            }

            response = es.search(index="pages", body=search_param)

            # do a lowercase check as well to prevent duplicate urls with case as the differentiator

            search_param = {
                "query": {
                    "term": {
                        "url.keyword": {
                            "value": request.args.get("url").lower()
                        }
                    }
                }
            }

            lower_response = es.search(index="pages", body=search_param)

        if response:
            return jsonify(response["hits"]["hits"])
        elif lower_response:
            return jsonify(lower_response["hits"]["hits"])
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
    return send_from_directory("static", path)
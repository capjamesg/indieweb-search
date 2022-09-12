import random

import mysql.connector
from elasticsearch import Elasticsearch
from flask import Blueprint, abort, jsonify, request

import config

from .constants import default_fields, to_delete
from .create_query import assemble_query
from .queries import (get_auto_suggest_query, get_date_ordered_query,
                      get_default_search_param)

es = Elasticsearch(["http://localhost:9200"])

main = Blueprint("main", __name__)


@main.route("/suggest")
def autosuggest():
    query = request.args.get("q")

    search_param = get_auto_suggest_query(query)

    response = es.search(index="pages", body=search_param)

    return jsonify({"results": response["suggest"]["simple_phrase"]}), 200


@main.route("/")
def home():
    # get accepted query params
    query = request.args.get("q")
    domain_param = request.args.get("domain")
    discover = request.args.get("discover")
    from_num = request.args.get("from")
    contains_js = request.args.get("js")
    site = request.args.get("site")
    inurl = request.args.get("inurl")
    category = request.args.get("category")
    mf2_property = request.args.get("mf2_property")
    sort = request.args.get("sort")

    index = request.args.get("index")

    if index is None:
        # default index is pages, but server might provide another one to use
        index = "pages"

    if not from_num:
        from_num = 1

    query = assemble_query(query, category, contains_js, inurl, mf2_property, site)

    fields = default_fields

    if discover and discover == "true":
        query = query + " AND (is_homepage:true)"
        fields = ["h_card"]

    if domain_param:
        domain = query.replace("who is ", "")

        # get domain homepage
        search_param = {
            "from": 0,
            "size": 1,
            "query": {"match": {"url": "https://" + domain.strip()}},
        }

    if sort and sort == "date_asc":
        search_param = get_date_ordered_query(query, "asc")
    elif sort and sort == "date_desc":
        search_param = get_date_ordered_query(query, "desc")
    else:
        search_param = get_default_search_param(query, fields)

    search_param["from"] = int(from_num)
    search_param["size"] = 10

    response = es.search(index=index, body=search_param)

    return (
        jsonify(
            {
                "results": response["hits"]["hits"],
                "count": response["hits"]["total"]["value"],
            }
        ),
        200,
    )


@main.route("/remove-from-index", methods=["POST"])
def remove_from_index():
    data = request.get_json()

    # remove from elasticsearch
    es.delete(index="pages", doc_type="page", id=data["id"])

    return jsonify({"status": "ok"})


@main.route("/create", methods=["POST"])
def create():
    data = request.get_json()

    total_docs_today = int(es.count(index="pages")["count"])

    es.index(index="pages", body=data, id=total_docs_today + 1)

    return jsonify({"status": "ok"})


@main.route("/evaluate")
def evaluate():
    term = request.args.get("term")
    data = request.get_json()

    if not term or not data:
        abort(400)

    request_body = {
        "requests": data,
        "metric": {
            "precision": {
                "k": 10,
                "relevant_rating_threshold": 1,
                "ignore_unlabeled": True,
            }
        },
    }

    rank_eval = es.rank_eval(term, body=request_body, index="pages")

    return jsonify({"result": rank_eval})


@main.route("/update", methods=["POST"])
def update():
    data = request.get_json()

    # get document with same url as data['url']
    search_param = {"query": {"match": {"url": data["url"]}}}

    response = es.search(index="pages", body=search_param)

    es.update(index="pages", id=response["hits"]["hits"][0]["_id"], body={"doc": data})

    return jsonify({"status": "ok"})


@main.route("/check", methods=["POST"])
def check():
    hash = request.args.get("hash")

    if hash:
        # get document with same hash as hash arg
        search_param = {"query": {"match": {"md5hash": hash}}}
    else:
        search_param = {
            "query": {"term": {"url.keyword": {"value": request.args.get("url")}}}
        }

    response = es.search(index="pages", body=search_param)

    # do a lowercase check as well to prevent duplicate urls with case as the differentiator

    if request.args.get("url"):
        search_param = {
            "query": {
                "term": {"url.keyword": {"value": request.args.get("url").lower()}}
            }
        }

        lower_response = es.search(index="pages", body=search_param)

        if request.args.get("url").endswith("/"):
            url = request.args.get("url")[:-1]
        else:
            url = request.args.get("url") + "/"

        # get opposite of submitted url in terms of trailing slash
        # this checks to see if a url is in the index with or without a trailing slash
        # this step is essential for preventing duplicates on the count of different trailing slashes
        search_param = {"query": {"term": {"url.keyword": {"value": url}}}}

        trailing_response = es.search(index="pages", body=search_param)

        search_param = {"query": {"term": {"url.keyword": {"value": url.lower()}}}}

        lower_trailing_response = es.search(index="pages", body=search_param)

        no_www = es.search(index="pages", body=search_param)

        search_param = {
            "query": {
                "term": {"url.keyword": {"value": url.lower().replace("www.", "")}}
            }
        }

        no_www = es.search(index="pages", body=search_param)
    else:
        lower_response = None
        trailing_response = None
        lower_trailing_response = None
        no_www = None

    if response:
        return jsonify(response["hits"]["hits"])
    elif lower_response:
        return jsonify(lower_response["hits"]["hits"])
    elif trailing_response:
        return jsonify(trailing_response["hits"]["hits"])
    elif lower_trailing_response:
        return jsonify(lower_trailing_response["hits"]["hits"])
    elif no_www:
        return jsonify(no_www["hits"]["hits"])
    else:
        return jsonify({"status": "not found"}), 404


@main.route("/count")
def show_num_of_pages():
    count = es.count(index="pages")

    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    return jsonify({"es_count": count, "domains": len(domains)})


@main.route("/random")
def random_page():
    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    # get random domain
    domain = domains[random.randint(0, len(domains) - 1)].strip()

    return jsonify({"domain": domain})


# return feeds associated with URL
@main.route("/feeds", methods=["GET", "POST"])
def get_feeds_for_url():
    website_url = request.form.get("website_url")

    if website_url:
        database = mysql.connector.connect(
            host="localhost",
            user=config.MYSQL_DB_USER,
            password=config.MYSQL_DB_PASSWORD,
            database="feeds",
        )

        cursor = database.cursor(buffered=True)

        cursor.execute("SELECT * FROM feeds WHERE website_url = %s", (website_url,))

        cursor.close()

        if cursor.fetchall():
            return jsonify(cursor.fetchall())
        else:
            return jsonify({"message": "No results matching this URL were found."})
    else:
        database = mysql.connector.connect(
            host="localhost",
            user=config.MYSQL_DB_USER,
            password=config.MYSQL_DB_PASSWORD,
            database="feeds",
        )
        cursor = database.cursor(buffered=True)

        cursor.execute("SELECT * FROM feeds")

        item_to_return = cursor.fetchall()

        cursor.close()

        return jsonify(item_to_return)


@main.route("/save", methods=["POST"])
def save_feed():
    result = request.get_json()["feeds"]

    for r in result:
        database = mysql.connector.connect(
            host="localhost",
            user=config.MYSQL_DB_USER,
            password=config.MYSQL_DB_PASSWORD,
            database="feeds",
        )
        cursor = database.cursor(buffered=True)

        cursor.execute(
            "SELECT * FROM feeds WHERE website_url = %s AND feed_url = %s AND mime_type = %s",
            (r["website_url"], r["feed_url"], r["mime_type"]),
        )

        if cursor.fetchone():
            # delete feed because it already exists to make room for the new feed
            cursor.execute(
                "DELETE FROM feeds WHERE website_url = %s AND feed_url = %s AND mime_type = %s",
                (r["website_url"], r["feed_url"], r["mime_type"]),
            )

        cursor.execute(
            "INSERT INTO feeds (website_url, feed_url, etag, discovered, mime_type) VALUES (%s, %s, %s, %s, %s)",
            (
                r["website_url"],
                r["feed_url"],
                r["etag"],
                r["discovered"],
                r["mime_type"],
            ),
        )

        database.commit()

        cursor.close()

    return jsonify({"message": "Feeds successfully saved."})

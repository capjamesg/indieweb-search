from flask import Flask, request, abort, jsonify, send_from_directory
from elasticsearch import Elasticsearch
import mysql.connector
import string
import random
import config

database = mysql.connector.connect(
    host="localhost",
    user=config.MYSQL_DB_USER,
    password=config.MYSQL_DB_PASSWORD,
    database="feeds"
)

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
            # if w == 0:
            #     final_query += query.split(" ")[w] + "^2"
            # else:
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
                        "fields": ["title^2", "description^1.5", "url^1.3", "category^0", "published^0", "keywords^0", "text^2.8", "h1^1.7", "h2^1.5", "h3^1.2", "h4^0.5", "h5^0.75", "h6^0.25", "domain^3"],
                        "minimum_should_match": "3<75%",
                    },
                },
                "script": {
                    "source": """
                        return _score + Math.log((1 + (doc['incoming_links'].value)) * 3.5) + Math.log((1 + (doc['word_count'].value)));
                    """
                },
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

    sort = request.args.get("sort")

    if sort and sort == "date_asc":
        search_param = {
            "from": int(from_num),
            "size": 10,
            "query": {
                "query_string": {
                    "query": query,
                    "fields": ["title^2", "description^1.5", "url^1.3", "category^0", "published^0", "keywords^0", "text^2.8", "h1^1.7", "h2^1.5", "h3^1.2", "h4^0.5", "h5^0.75", "h6^0.25", "domain^3"],
                    "minimum_should_match": "3<75%",
                },
            },
            "sort": [
                {
                    "published": {
                        "order": "asc"
                    }
                }
            ]
        }
    elif sort and sort == "date_desc":
        search_param = {
            "from": int(from_num),
            "size": 10,
            "query": {
                "query_string": {
                    "query": query,
                    "fields": ["title^2", "description^1.5", "url^1.3", "category^0", "published^0", "keywords^0", "text^2.8", "h1^1.7", "h2^1.5", "h3^1.2", "h4^0.5", "h5^0.75", "h6^0.25", "domain^3"],
                    "minimum_should_match": "3<75%",
                },
            },
            "sort": [
                {
                    "published": {
                        "order": "desc"
                    }
                }
            ]
        }

    #* saturation(doc['pagerank'].value, 10)"

    response = es.search(index="pages", body=search_param)

    return response

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

        if request.args.get("url"):

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
            
            if request.args.get("url").endswith("/"):
                url = request.args.get("url")[:-1]
            else:
                url = request.args.get("url") + "/"

            # get opposite of submitted url in terms of trailing slash
            # this checks to see if a url is in the index with or without a trailing slash
            # this step is essential for preventing duplicates on the count of different trailing slashes
            search_param = {
                "query": {
                    "term": {
                        "url.keyword": {
                            "value": url
                        }
                    }
                }
            }

            trailing_response = es.search(index="pages", body=search_param)

            search_param = {
                "query": {
                    "term": {
                        "url.keyword": {
                            "value": url.lower()
                        }
                    }
                }
            }

            lower_trailing_response = es.search(index="pages", body=search_param)
        else:
            lower_response = None
            trailing_response = None
            lower_trailing_response = None

        if response:
            return jsonify(response["hits"]["hits"])
        elif lower_response:
            return jsonify(lower_response["hits"]["hits"])
        elif trailing_response:
            return jsonify(trailing_response["hits"]["hits"])
        elif lower_trailing_response:
            return jsonify(lower_trailing_response["hits"]["hits"])
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

# return feeds associated with URL
@app.route("/feeds", methods=["GET", "POST"])
def get_feeds_for_url():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    if request.method == "POST":
        website_url = request.form.get("website_url")

        if website_url:
            cursor = database.cursor(buffered=True)

            cursor.execute("SELECT * FROM feeds WHERE website_url = %s", (website_url,))

            cursor.close()

            if cursor.fetchall():
                return jsonify(cursor.fetchall())
            else:
                return jsonify({"message": "No results matching this URL were found."})
        else:
            cursor = database.cursor(buffered=True)

            cursor.execute("SELECT * FROM feeds")
            
            item_to_return = cursor.fetchall()

            cursor.close()

            return jsonify(item_to_return)

    return jsonify({"message": "Method not allowed."}), 405

@app.route("/save", methods=["POST"])
def save_feed():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    if request.method == "POST":
        result = request.get_json()["feeds"]

        for r in result:
            cursor = database.cursor(buffered=True)

            cursor.execute("SELECT * FROM feeds WHERE website_url = %s AND feed_url = %s AND mime_type = %s", (r["website_url"], r["feed_url"], r["mime_type"]))

            if cursor.fetchone():
                # delete feed because it already exists to make room for the new feed
                cursor.execute("DELETE FROM feeds WHERE website_url = %s AND feed_url = %s AND mime_type = %s", (r["website_url"], r["feed_url"], r["mime_type"]))

            cursor.execute("INSERT INTO feeds (website_url, feed_url, etag, discovered, mime_type) VALUES (%s, %s, %s, %s, %s)", (r["website_url"], r["feed_url"], r["etag"], r["discovered"], r["mime_type"]))

            database.commit()

            cursor.close()

        return jsonify({"message": "Feeds successfully saved."})

    return 200

@app.route("/crawled")
def get_crawled_sites():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)
        
    cursor = database.cursor(buffered=True)
    
    cursor.execute("SELECT * FROM crawled")

    item_to_return = cursor.fetchall()

    cursor.close()
    
    return jsonify(item_to_return)

@app.route("/create_crawled", methods=["POST"])
def create_crawled_site():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)
        
    if request.method == "POST":
        url = request.form.get("url")
        
        if url:
            cursor = database.cursor(buffered=True)
            
            cursor.execute("SELECT * FROM crawled WHERE url = %s", (url,))
            
            if cursor.fetchone():
                return jsonify({"message": "This site has already been crawled."})
            else:
                cursor.execute("INSERT INTO crawled (url) VALUES (%s)", (url,))
                
                database.commit()

                cursor.close()
                
                return jsonify({"message": "Site successfully added to the crawled table."})
        else:
            return jsonify({"message": "No URL was provided."})
        
    return jsonify({"message": "Method not allowed."}), 405

@app.route("/crawl_queue")
def get_crawl_queue():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    cursor = database.cursor(buffered=True)

    cursor.execute("SELECT * FROM crawl_queue")

    item_to_return = cursor.fetchall()

    cursor.close()

    return jsonify(item_to_return)

@app.route("/sitemaps")
def get_sitemaps():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    cursor = database.cursor(buffered=True)

    cursor.execute("SELECT * FROM sitemaps")

    item_to_return = cursor.fetchall()

    cursor.close()

    return jsonify(item_to_return)

@app.route("/create_sitemap", methods=["POST"])
def create_sitemap():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    if request.method == "POST":
        website_url = request.form.get("domain")
        sitemap_url = request.form.get("sitemap_url")

        if website_url:
            cursor = database.cursor(buffered=True)

            cursor.execute("SELECT * FROM sitemaps WHERE domain = %s", (website_url,))

            if cursor.fetchone():
                return jsonify({"message": "Sitemap already exists."})
            else:
                cursor.execute("INSERT INTO sitemaps (domain, sitemap_url) VALUES (%s, %s)", (website_url, sitemap_url))

                database.commit()

                cursor.close()

                return jsonify({"message": "Sitemap successfully created."})
        else:
            return jsonify({"message": "No website URL was provided."})

    return jsonify({"message": "Method not allowed."}), 405

@app.route("/create_websub", methods=["POST"])
def create_websub():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    if request.method == "POST":
        result = request.get_json()

        cursor = database.cursor(buffered=True)

        cursor.execute("SELECT * FROM websub WHERE url = %s", (result["website_url"],))

        if cursor.fetchone():
            cursor.execute("DELETE FROM websub WHERE url = %s", (result["website_url"],))

        random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))

        cursor.execute("INSERT INTO websub (url, random_string) VALUES (%s, %s)", (result["website_url"], random_string))

        database.commit()

        cursor.close()

        return jsonify({"key": random_string})

    return jsonify({"message": "Method not allowed."}), 405

@app.route("/feed_breakdown")
def get_feed_breakdown():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    cursor = database.cursor(buffered=True)

    cursor.execute("select mime_type, count(mime_type) from feeds group by mime_type order by count(mime_type) desc;")

    feeds = [[mime_type, int(count)] for mime_type, count in cursor.fetchall()]

    cursor.close()

    return jsonify(feeds)

@app.route("/update_feed", methods=["POST"])
def update_feed():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    cursor = database.cursor(buffered=True)

    item = request.get_json()

    cursor.execute("SELECT * FROM feeds WHERE feed_url = %s", (item.get("feed_url"),))

    feeds = cursor.fetchone()

    if feeds and len(feeds) > 0:
        cursor.execute("UPDATE feeds SET etag = %s, last_modified = %s WHERE feed_url = %s", (item.get("etag"), item.get("last_modified"), item.get("feed_url")))

        database.commit()

        cursor.close()

        return 200
    
    abort(400)

@app.route("/websub/<string:id>", methods=["GET", "POST"])
def websub(id):
    cursor = database.cursor(buffered=True)

    subscriptions = cursor.execute("SELECT * FROM websub WHERE random_string = %s", (id,)).fetchone()

    if request.method == "GET":
        if id in subscriptions:
            challenge = request.args.get("hub.challenge")

            return challenge, 200
        else:
            return "", 404

    if subscriptions and len(subscriptions) > 0:
        # treat "fat pings" as regular requests because we need to crawl a page as is
        # reference: https://indieweb.org/How_to_publish_and_consume_WebSub#How_to_Subscribe

        cursor.execute("INSERT INTO crawl_queue (url) VALUES (%s)", (subscriptions[0][0],))

        database.commit()

        cursor.close()

        return "", 200
    else:
        return "", 400
from flask import request, abort, jsonify, Blueprint
from elasticsearch import Elasticsearch
import mysql.connector
import random
import config
import json
import csv

es = Elasticsearch(['http://localhost:9200'])

stats = Blueprint('stats', __name__)

@stats.route("/count")
def show_num_of_pages():
    count = es.count(index="pages")

    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    return jsonify({"es_count": count, "domains": len(domains)})

@stats.route("/random")
def random_page():
    if request.args.get("pw") != config.ELASTICSEARCH_PASSWORD:
        return abort(401)
        
    # read domains.txt file
    with open("domains.txt", "r") as f:
        domains = f.readlines()

    # get random domain
    domain = domains[random.randint(0, len(domains) - 1)].strip()

    return jsonify({"domain": domain})

@stats.route("/crawled")
def get_crawled_sites():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    database = mysql.connector.connect(
        host="localhost",
        user=config.MYSQL_DB_USER,
        password=config.MYSQL_DB_PASSWORD,
        database="feeds"
    )
        
    cursor = database.cursor(buffered=True)
    
    cursor.execute("SELECT * FROM crawled")

    item_to_return = cursor.fetchall()

    cursor.close()
    
    return jsonify(item_to_return)

@stats.route("/crawl_queue")
def get_crawl_queue():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    database = mysql.connector.connect(
        host="localhost",
        user=config.MYSQL_DB_USER,
        password=config.MYSQL_DB_PASSWORD,
        database="feeds"
    )

    cursor = database.cursor(buffered=True)

    cursor.execute("SELECT * FROM crawl_queue")

    item_to_return = cursor.fetchall()

    cursor.close()

    return jsonify(item_to_return)

@stats.route("/sitemaps")
def get_sitemaps():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    database = mysql.connector.connect(
        host="localhost",
        user=config.MYSQL_DB_USER,
        password=config.MYSQL_DB_PASSWORD,
        database="feeds"
    )

    cursor = database.cursor(buffered=True)

    cursor.execute("SELECT * FROM sitemaps")

    item_to_return = cursor.fetchall()

    cursor.close()

    return jsonify(item_to_return)

@stats.route("/feed_breakdown")
def get_feed_breakdown():
    if not request.headers.get("Authorization") or request.headers.get("Authorization") != config.ELASTICSEARCH_API_TOKEN:
        abort(401)

    database = mysql.connector.connect(
        host="localhost",
        user=config.MYSQL_DB_USER,
        password=config.MYSQL_DB_PASSWORD,
        database="feeds"
    )

    cursor = database.cursor(buffered=True)

    cursor.execute("select mime_type, count(mime_type) from feeds group by mime_type order by count(mime_type) desc;")

    feeds = [[mime_type, int(count)] for mime_type, count in cursor.fetchall()]

    cursor.close()

    return jsonify(feeds)

@stats.route("/special_stats")
def get_special_stats():
	with open('top_ten_links.csv', 'r') as f:
		reader = csv.reader(f)
		top_ten_links = list(reader)

	with open('link_microformat_instances.json', 'r') as f:
		link_microformat_instances = json.load(f)

	return jsonify({"top_ten_links": top_ten_links, "link_microformat_instances": link_microformat_instances})
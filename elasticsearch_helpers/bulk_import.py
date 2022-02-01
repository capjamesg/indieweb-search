import sqlite3

from elasticsearch import Elasticsearch, helpers

es = Elasticsearch(["http://localhost:9200"])

connection = sqlite3.connect("search.db")


def change_to_json(database_result):
    columns = [column[0] for column in database_result.description]

    result = [dict(zip(columns, row)) for row in database_result]

    return result


# get last indexed document

id = int(es.count(index="pages")["count"])

with connection:
    cursor = connection.cursor()

    all_posts_count = cursor.execute("SELECT count(url) FROM posts").fetchone()

    pages = cursor.execute("SELECT * FROM posts LIMIT 500 OFFSET {};".format(id))

    doc = change_to_json(pages)

    print("processed doc")

    resp = helpers.bulk(es, doc, index="pages")
    print("finished {}".format(id))

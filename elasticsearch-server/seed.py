import mysql.connector
import config

database = mysql.connector.connect(
	host="localhost",
	user=config.MYSQL_DB_USER,
	password=config.MYSQL_DB_PASSWORD,
	database="feeds"
)

cursor = database.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS feeds (
    website_url text,
    feed_url text,
    etag text,
    discovered text,
    mime_type text
""")

print("created feeds table")

cursor.execute("""CREATE TABLE IF NOT EXISTS sitemaps (
    domain text,
    sitemap_url text
""")

print("created sitemaps table")

cursor.execute("""CREATE TABLE IF NOT EXISTS crawled (
    domain text,
    crawled_on text
""")

print("created crawled table")

cursor.execute("""CREATE TABLE IF NOT EXISTS websub (
    url text,
    random_string text
""")

print("created websub table")

cursor.execute("""CREATE TABLE IF NOT EXISTS crawl_queue (
    url text
""")

print("created crawl_queue table")

print("the database is now ready for use on the elasticsearch back-end web server")
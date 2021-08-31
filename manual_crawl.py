import crawler.url_handling as url_handling
import sqlite3

final_urls = {
    "https://indieweb.org/accessibility": ""
}

all_links = []
external_links = {}
discovered_urls = {}
broken_urls = []

pages_indexed = 0

connection = sqlite3.connect("search.db")

with connection:
    cursor = connection.cursor()

    url_handling.crawl_urls(final_urls, [], cursor, 0, 0, [], all_links, external_links, discovered_urls, broken_urls, list(final_urls.keys()), "indieweb.org")

print("crawl finished")
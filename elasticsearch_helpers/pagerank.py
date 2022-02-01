import sqlite3

import networkx as nx
import tldextract
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator

from crawler import page_info, url_handling

connection = sqlite3.connect("search.db")

indexed = {}
incoming = {}
domains = {}

G = nx.DiGraph(nx.path_graph(4))

with connection:
    cursor = connection.cursor()

    # get unique domains in database
    domains_db = cursor.execute("SELECT DISTINCT url FROM posts;").fetchall()

    for domain in domains_db:
        # get domain name
        name = tldextract.extract(domain[0])

        domains[".".join(part for part in name if part)] = ""

    for d in domains:
        all_pages_in_domain = cursor.execute(
            "SELECT url, page_content FROM posts WHERE url LIKE ?", ("%" + d + "%",)
        ).fetchall()

        for page in all_pages_in_domain:
            page_desc_soup = BeautifulSoup(page[1], "lxml")

            G.add_node(page[0])

            all_links = page_desc_soup.find_all("a")

            for link in all_links:
                try:
                    G.add_node(link.text)
                    G.add_edge(link.text, page[0])
                except:
                    print("one broken")

        print(d)

pr = nx.pagerank(G, alpha=0.9, max_iter=100, tol=1e-06)

print(pr)

# update all rows in db to include their pagerank

with connection:
    cursor = connection.cursor()
    for url, page_rank in pr.items():
        print(url, page_rank)
        cursor.execute(
            "UPDATE posts SET pagerank = ? WHERE url = ?",
            (
                page_rank,
                url,
            ),
        )

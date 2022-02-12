import concurrent.futures
import logging

import constants
import recrawl_url
import requests


def process_crawl_queue_from_websub():
    r = requests.get(
        "https://es-indieweb-search.jamesg.blog/crawl_queue", headers=constants.HEADERS
    )

    pages_indexed = 0

    to_crawl = r.json()

    domains_indexed = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [
            executor.submit(recrawl_url.schedule_crawl_of_one_url, item, item, None)
            for item in to_crawl
        ]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                pages_indexed += 1

                print(f"PAGES INDEXED: {pages_indexed}")
                logging.info(f"PAGES INDEXED: {pages_indexed}")

                try:
                    domain = url_indexed.split("/")[2]

                    domains_indexed[domain] = domains_indexed.get(domain, 0) + 1

                    if domains_indexed[domain] > 50:
                        print(f"50 urls have been crawled on {domain}, skipping")
                        continue

                    url_indexed, _ = future.result()

                    if url_indexed is None:
                        futures = []
                        break

                except Exception as e:
                    print(e)
                    pass

                futures.remove(future)

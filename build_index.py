import concurrent.futures
import datetime
import ipaddress
import urllib.robotparser
from typing import List

import indieweb_utils
# import cProfile
import mf2py
import pika
import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
# ignore warning about http:// connections
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import config
import crawler.verify_and_process as verify_and_process
from write_logs import write_log

es = Elasticsearch(config.ELASTICSEARCH_HOST)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

start_time = datetime.datetime.now()

broken_urls = []

external_links = {}

links = []

# Dict to track newly discovered urls
# Key = URL discovered
# Value = Page to process
discovered_urls = {}

headers = {"Authorization": config.ELASTICSEARCH_API_TOKEN}


def process_domain(site: str) -> List[list]:
    """
    Processes a domain and executes a function that crawls all pages on the domain.
    This function keeps track of URLs that have been crawled, the hashes of pages that have been crawled
    and other key information required to manage a site crawl.
    """
    final_urls = {}

    rp = urllib.robotparser.RobotFileParser()

    protocol = "https://"

    rp.set_url(f"{protocol}{site}/robots.txt")

    sitemap_urls = rp.site_maps() or []

    write_log("CRAWL BEGINNING", site)

    # Parse sitemap indexes
    for u in sitemap_urls:
        r = requests.get(
            u,
            verify=False,
            headers=config.SEARCH_HEADERS,
            timeout=5,
            allow_redirects=True,
        )
        if r.status_code == 200:
            # parse with bs4
            soup = BeautifulSoup(r.text, "html.parser")
            if soup.find("sitemapindex"):
                # find all the urls
                all_sitemaps = soup.find_all("loc")
                for sitemap in all_sitemaps:
                    sitemap_urls.append(sitemap.text)
                    # write_log("will crawl URLs in {} sitemap".format(sitemap.text))
                    write_log(f"will crawl URLs in {sitemap.text} sitemap", site)
            else:
                # write_log("will crawl URLs in {} sitemap".format(u))
                write_log(f"will crawl URLs in {u} sitemap", site)

    sitemap_urls = list(set(sitemap_urls))

    # Added just to make sure the homepage is in the initial crawl queue
    if len(sitemap_urls) > 2:
        final_urls[f"http://{site}"] = ""

    for s in sitemap_urls:
        # Only URLs not already discovered will be added by this code
        # Lastmod dates will be added to the final_url value related to the URL if a lastmod date is available
        feed = requests.get(
            s,
            headers=config.SEARCH_HEADERS,
            timeout=5,
            verify=False,
            allow_redirects=True,
        )

        soup = BeautifulSoup(feed.content, "lxml")

        urls = list(soup.find_all("url"))

        headers = {"Authorization": config.ELASTICSEARCH_API_TOKEN}

        r = requests.post(
            "https://es-indieweb-search.jamesg.blog/create_sitemap",
            data={"sitemap_url": s, "domain": site},
            headers=headers,
        )

        if r.status_code == 200:
            # write_log(r.text)
            # write_log("sitemaps added to database for {}".format(site))
            write_log(f"sitemaps added to database for {site}", site)
        else:
            # write_log("ERROR: sitemap not added for {} (status code {})".format(site, r.status_code))
            write_log(
                f"sitemap not added for {site} (status code {r.status_code})", site
            )

        for u in urls:
            if "/tag/" in u.find("loc").text:
                continue

            canonicalized_url = indieweb_utils.canonicalize_url(
                site, site, u.find("loc").text
            )

            if u.find("lastmod"):
                final_urls[canonicalized_url] = u.find("lastmod").text
            else:
                final_urls[canonicalized_url] = ""

    # crawl budget is 15,000 URLs
    return 15000, final_urls, protocol, rp


def get_feeds(site: str) -> list:
    """
    Returns a list of feed URLs for a given site.
    """

    r = requests.post(
        "https://es-indieweb-search.jamesg.blog/feeds",
        headers=headers,
        data={"website_url": site},
    )

    if r.status_code == 200 and r.json() and not r.json().get("message"):
        write_log(f"feeds retrieved for {site}", site)
        feeds = r.json()
    elif r.status_code == 200 and r.json() and r.json().get("message"):
        # write_log("Result from URL request to /feeds endpoint on elasticsearch server: {}".format(r.json()["message"]))
        write_log(
            "Result from URL request to /feeds endpoint on elasticsearch server: {}".format(
                r.json()["message"]
            ),
            site,
        )
        feeds = []
    elif r.status_code == 200 and not r.json():
        # write_log("No feeds retrieved for {} but still 200 response".format(site))
        write_log(f"No feeds retrieved for {site} but still 200 response", site)
        feeds = []
    else:
        # write_log("ERROR: feeds not retrieved for {} (status code {})".format(site, r.status_code))
        write_log(f"feeds not retrieved for {site} (status code {r.status_code})", site)
        feeds = []

    return feeds


def get_urls_to_crawl(
    protocol: str, site: str, final_urls: dict, web_page_hashes: dict
) -> tuple:
    r = requests.get(
        "https://es-indieweb-search.jamesg.blog/to_crawl",
        headers=headers,
        data={"website_url": site},
    )

    if r.status_code == 200 and r.json() and not r.json().get("urls"):
        write_log(f"{site} has urls that need to be crawled", site)
        all_urls = r.json().get("urls")

        for url in all_urls:
            url_object = url[0]
            hash = [1]
            final_urls[url_object] = ""
            web_page_hashes[hash] = url_object
    else:
        write_log(
            f"{site} has no urls that need to be crawled (status code {r.status_code})",
            site,
        )

    if len(final_urls) == 0:
        final_urls[f"{protocol}{site}"] = ""

    crawl_queue = list(final_urls.keys())

    return final_urls, crawl_queue, web_page_hashes


def build_index(site: str) -> List[list]:
    """
    Main function to crawl a specified set of sites.

    This function manages a concurrent.futures pool of threads to crawl websites.

    This function calls on the crawler/verify_and_process.py functions to crawl pages.

    This function also manages a list of various values that are required to manage a crawl
    (i.e. crawl speed, numbers of URLs indexed).

    :param site: The site to crawl
    :type site: str

    :return: The page indexed and the number of URLs discovered
    :rtype: List[int, list]
    """
    # do not index IPs
    # sites must have a domain name to qualify for inclusion in the index
    try:
        if ipaddress.ip_address(site):
            return
    except:
        pass

    # read crawl_queue.txt
    crawl_budget, final_urls, protocol, rp = process_domain(site)

    feeds = get_feeds(site)

    write_log(f"processing {site}. crawl budget: {crawl_budget}", site)

    # initialize variables for crawl
    indexed = 0
    valid_count = 0
    indexed_list = {}
    all_feeds = []
    discovered_feeds_dict = {}
    web_page_hashes = {}
    crawl_depths = {}
    average_crawl_speed = []
    homepage_meta_description = ""
    budget_spent = 0

    session = requests.Session()

    try:
        h_card = mf2py.Parser(protocol + site)
    except:
        h_card = []
        write_log(f"no h-card could be found on {site} home page", site)

    # get home page title
    try:
        r = session.get(protocol + site, headers=config.SEARCH_HEADERS, timeout=5)
        soup = BeautifulSoup(r.content, "lxml")
        home_page_title = soup.find("title").text
    except:
        home_page_title = ""

    final_urls, crawl_queue, web_page_hashes = get_urls_to_crawl(
        protocol, site, final_urls, web_page_hashes
    )

    for url in crawl_queue:
        crawl_depth = 0

        if crawl_depths.get("url"):
            crawl_depth = crawl_depths.get("url")
            if crawl_depth > 5:
                # write_log("crawl depth for {} is {}".format(url, crawl_depth))
                write_log(f"crawl depth for {url} is {crawl_depth}", site)

        if indexed_list.get(url):
            continue

        (
            url_indexed,
            discovered,
            valid,
            discovered_feeds,
            web_page_hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        ) = verify_and_process.crawl_urls(
            final_urls,
            indexed,
            links,
            external_links,
            discovered_urls,
            crawl_queue,
            site,
            crawl_budget,
            url,
            [],
            feeds,
            site,
            session,
            web_page_hashes,
            average_crawl_speed,
            homepage_meta_description,
            True,
            h_card,
            crawl_depth,
            home_page_title,
            es,
            rp,
        )

        if valid:
            valid_count += 1

        if web_page_hash is not None:
            web_page_hashes[web_page_hash] = url

        average_crawl_speed.extend(average_crawl_speed)

        if len(average_crawl_speed) > 100:
            average_crawl_speed = average_crawl_speed[:100]

        if (
            average_crawl_speed
            and len(average_crawl_speed)
            and (len(average_crawl_speed) / len(average_crawl_speed) > 4)
        ):
            write_log(
                f"average crawl speed is {len(average_crawl_speed) / len(average_crawl_speed)}, stopping crawl",
                site,
            )
            with open("failed.txt", "a") as f:
                f.write(
                    f"{site} average crawl speed is {len(average_crawl_speed) / len(average_crawl_speed)}, stopping crawl \n"
                )

            crawl_queue = []

        indexed += 1

        budget_spent += budget_used

        write_log(
            f"{site} ({url_indexed}) - indexed: {indexed} / budget spent: {budget_spent} / budget for crawl: {crawl_budget}",
            site,
        )

        if budget_spent > crawl_budget:
            break

        indexed_list[url_indexed] = True
        web_page_hashes[web_page_hash] = url

        for f in discovered_feeds:
            if discovered_feeds_dict.get(f.get("feed_url")) is None:
                all_feeds.append(f)
                feeds.append(f.get("feed_url"))
                discovered_feeds_dict[f.get("feed_url")] = True

        for key, value in discovered.items():
            if not indexed_list.get(key):
                write_log(f"{key} not indexed, added", site)
                crawl_queue.append(key)

            crawl_depths[key] = value

    headers["Content-Type"] = "application/json"

    # exclude wordpress json feeds for now
    # only save first 25 feeds
    feeds = [f for f in all_feeds[:25] if "wp-json" not in f]

    # turn indexed_list into a list of strings
    current_date = datetime.date.today().strftime("%Y-%m-%d")

    indexed_list = [[url, current_date] for url in list(indexed_list.keys())]

    return url_indexed, discovered


def callback(ch, method, properties, body):
    ch.basic_ack(delivery_tag=method.delivery_tag)

    print("[x] Received %r" % body)
    build_index(body.decode("utf-8"))


def consumer():
    # credentials = pika.PlainCredentials(
    #     config.RABBITMQ_USERNAME, config.RABBITMQ_PASSWORD
    # )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost") #, credentials=credentials)
    )

    channel = connection.channel()

    channel.basic_consume(
        queue="domains_to_crawl", auto_ack=True, on_message_callback=callback
    )

    channel.start_consuming()


def main():
    futures = []

    sites_indexed = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(consumer) for _ in range(0, 5)]

        while len(futures) > 0:
            for future in concurrent.futures.as_completed(futures):
                sites_indexed += 1

                write_log(f"SITES INDEXED: {sites_indexed}")

                try:
                    url_indexed, _ = future.result()

                    if url_indexed is None:
                        futures = []
                        break
                except Exception as e:
                    print(e)
                    raise e

                futures.remove(future)
                futures.append(executor.submit(consumer))


if __name__ == "__main__":
    # cProfile.run("main()", "profile.txt")
    main()

import csv
import datetime
import json
import logging
from urllib.parse import urlparse as parse_url

import indieweb_utils
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

from elasticsearch_helpers.scroll import scroll

logging.basicConfig(
    filename=f"logs/link_graph/{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log",
    datefmt="%Y-%m-%d %H:%M:%S",
)

es = Elasticsearch(["http://localhost:9200"])

body = {"query": {"match_all": {}}}

domain_links = {}
links = {}

link_microformat_instances = {}

LINK_MICROFORMATS = [
    ("u-in-reply-to", 0.1),
    ("u-like-of", 0.5),
    ("u-repost-of", 0.75),
    ("u-bookmark-of", 0.75),
    ("u-url", 0),
    ("u-favorite-of", 0.5),
    ("u-quotation-of", 0.75),
    ("u-invitee", 0),
]


def get_link_weight(l: dict) -> tuple:
    for microformat, weight in LINK_MICROFORMATS:
        if microformat in l.get("class"):
            return microformat, weight

    return "", 0


def get_all_links(h: dict, f: csv.DictWriter) -> None:
    # don't count links on pages that specified nofollow in the X-Robots-Tag header
    if (
        h["_source"].get("page_is_nofollow")
        and h["_source"].get("page_is_nofollow") == "true"
    ):
        return

    try:
        soup = BeautifulSoup(h["_source"]["page_content"], "html.parser")
    except:
        soup = BeautifulSoup(h["_source"]["page_content"], "html5lib")

    links = soup.find_all("a")

    # check for nofollow or none meta values
    check_if_no_index = soup.find("meta", {"name": "robots"})

    if (
        check_if_no_index
        and check_if_no_index.get("content")
        and (
            "noindex" in check_if_no_index.get("content")
            or "none" in check_if_no_index.get("content")
        )
    ):
        print(f"all links on {h['_source']['url']} marked as nofollow, skipping")
        logging.info(f"all links on {h['_source']['url']} marked as nofollow, skipping")
        return

    links_on_page = {}

    for l in links:
        if l.get("href") == None:
            continue

        # skip nofollow links
        if l.get("rel") and "nofollow" in l["rel"]:
            continue

        link = indieweb_utils.canonicalize_url(
            l["href"], h["_source"]["domain"], l["href"]
        )

        link = link.strip("/").split("?")[0].replace("#", "")

        # don't count the same link twice
        if links_on_page.get(link):
            continue

        links_on_page[link] = link

        mf2_attribute = ""

        weight = 0

        if l.get("class"):
            mf2_attribute, weight = get_link_weight(l)

        if link_microformat_instances.get(mf2_attribute):
            link_microformat_instances[mf2_attribute] += 1
        else:
            link_microformat_instances[mf2_attribute] = 1

        try:
            link_domain = link.split("/")[2].replace("www.", "").lower()

            if domain_links.get(link_domain):
                domain_links[link_domain] += weight + 1
            else:
                domain_links[link_domain] = weight + 1

            # don't count links to someone's own site
            if h["_source"]["domain"] == link_domain:
                continue
        except:
            continue

        csv.writer(f).writerow([h["_source"]["url"], link, link_domain])


def write_links_to_file():
    count = 0

    with open("links.csv", "w+") as f:
        for hits in scroll(es, "pages", body, "3m", 40):
            for h in hits:
                print(str(count) + " " + h["_source"]["url"])
                logging.info(str(count) + " " + h["_source"]["url"])
                get_all_links(h, f)
                count += 1

    # write domain_links to file
    # may be a useful metric for determining overall domain authority
    with open("domain_links.json", "w+") as f:
        json.dump(domain_links, f)

    with open("all_domains.txt", "w+") as f:
        for domain in domain_links.keys():
            f.write(domain.lower() + "\n")


def get_domain_internal_link_count() -> list:
    # Open links file
    links = {}
    count = 0
    # Create dictionary with the number of times each domain appears
    for line in open("links.csv", "r"):
        line = line.strip().lower()

        link = line.split(",")

        # get domain of link
        try:
            domain_1 = link[0].split("//")[1].split("/")[0]
            domain_2 = link[1].split("//")[1].split("/")[0]
            if domain_1 != domain_2:
                if links.get(link[1]):
                    links[link[1]] = links[link[1]] + 1
                else:
                    links[link[1]] = 1
            count += 1
            print(count)
            logging.info(count)
        except:
            print("error with link")
            logging.info("error with link")

    # write links to all_links_final.json
    with open("all_links_final.json", "w+") as f:
        json.dump(links, f)

    with open("all_links_final.json", "r") as f:
        links = json.load(f)

    with open("all_domains.txt", "r") as file:
        domain_list = file.read().splitlines()

    domains = {k: "" for k in domain_list}

    return domains


def update_incoming_links_attribute_for_url(domains: list) -> None:
    incoming_links_count = 0

    for link, link_count in links.items():
        found = "no"
        link_domain = link.split("/")

        if link_domain:
            link_domain = link_domain[2].replace("www.", "").lower()
        else:
            continue

        # do not search elasticsearch if a domain is not in the index
        # checking if each link in the "links.csv" file is in the index is inefficient and slow
        if domains.get(link_domain) is None:
            continue

        while found == "no":
            search_param = {
                "query": {
                    "term": {
                        "url.keyword": {"value": link.replace("http://", "https://")}
                    }
                }
            }

            response = es.search(index="pages", body=search_param)

            if len(response["hits"]["hits"]) > 0:
                found = "yes"

            # look for a link in all variations
            tests = [
                link.replace("https://", "http://"),
                link.replace("http://", "https://").strip("/"),
                link.replace("https://", "http://").strip("/"),
                link.replace("www.", ""),
                link.replace("www.", "").strip("/"),
                link.replace("www.", "").strip("/").replace("https://", "http://"),
                link.replace("www.", "").strip("/").replace("https://", "http://"),
            ]

            for t in tests:
                search_param = {"query": {"term": {"url.keyword": {"value": t}}}}

                response = es.search(index="pages", body=search_param)

                if len(response["hits"]["hits"]) > 0:
                    found = "yes"
                    break

            print("No results for " + link + ", skipping")
            logging.info("No results for " + link + ", skipping")

            found = "none"

        if found == "none":
            continue

        try:
            link_domain = link.split("/")[2].lower().replace("www.", "")

            referring_domains = domain_links.get(link_domain)
        except:
            referring_domains = 0

        es.update(
            index="pages",
            id=response["hits"]["hits"][0]["_id"],
            body={
                "doc": {
                    "incoming_links": link_count,
                    "referring_domains_to_site": referring_domains,
                }
            },
        )

        full_link = response["hits"]["hits"][0]["_source"]["url"]

        incoming_links_count += 1

        print(incoming_links_count, full_link)
        logging.info(incoming_links_count, full_link)


def calculate_aggregate_statistics(links: list) -> None:
    print("calculating top linked assets")
    logging.info("calculating top linked assets")

    # sort URLs by number of incoming links
    links = {k: v for k, v in reversed(sorted(links.items(), key=lambda item: item[1]))}

    link_origin = [i for i in links.keys()]
    link_value = [i for i in links.values()]

    top_ten = [[origin, value] for origin, value in zip(link_origin, link_value)][:10]

    with open("top_ten_links.csv", "w+") as f:
        csv.writer(f).writerows(top_ten)

    print("calculated top 10 linked assets")
    logging.info("calculated top 10 linked assets")

    with open("link_microformat_instances.json", "w+") as f:
        json.dump(link_microformat_instances, f)

    print("calculated link microformat instances")
    logging.info("calculated link microformat instances")


def main():
    logging.info(
        f"Starting link graph build at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    write_links_to_file()
    domains = get_domain_internal_link_count()
    update_incoming_links_attribute_for_url(domains)
    calculate_aggregate_statistics(links)


main()

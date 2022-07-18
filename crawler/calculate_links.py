import json
import logging
from urllib.parse import urlparse as parse_url

import indieweb_utils
import pika

domain_links = {}
links = {}

link_microformat_instances = {}

connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))

channel = connection.channel()

channel.queue_declare("data")


def get_task(source: str, destination: str, weight: int) -> dict:
    task_data = {
        "server": "indieweb-search",
        "task": "process_links",
        "data": {"source": source, "destination": destination, "weight": weight},
    }

    return task_data


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


def get_all_links(url: str, is_no_follow: bool, soup: str) -> None:
    # don't count links on pages that specified nofollow in the X-Robots-Tag header
    if is_no_follow:
        return

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
        print(f"all links on {url} marked as nofollow, skipping")
        logging.info(f"all links on {url} marked as nofollow, skipping")
        return

    links_on_page = {}

    domain = parse_url(url).netloc

    for l in links:
        if l.get("href") == None:
            continue

        # skip nofollow links
        if l.get("rel") and "nofollow" in l["rel"]:
            continue

        link = indieweb_utils.canonicalize_url(l["href"], domain, l["href"])

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
            if domain == link_domain:
                continue
        except:
            continue

        task_data = get_task(url, l.get("href"), weight)

        channel.basic_publish(
            exchange="", routing_key="data", body=json.dumps(task_data)
        )

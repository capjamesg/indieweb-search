import logging

import indieweb_utils
import requests

from crawler.verify_and_process import crawl_urls


def schedule_crawl_of_one_url(url, site_url, session):
    if session == None:
        session = requests.Session()

    url = indieweb_utils.canonicalize_url(url, site_url)

    crawl_urls(
        {url: ""},
        [],
        0,
        [],
        [],
        {},
        [url],
        site_url,
        10,
        url,
        [],
        [],
        url.split("/")[2],
        session,
        {},
        [],
        "",
        False,
        [],
        0,
    )

    print(f"crawled {url} url")

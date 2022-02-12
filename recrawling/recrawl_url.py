import requests

from crawler.verify_and_process import crawl_urls


def schedule_crawl_of_one_url(url, site_url, session):
    if session == None:
        session = requests.Session()
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

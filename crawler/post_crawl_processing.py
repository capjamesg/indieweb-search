import logging

import requests


def save_feeds_to_database(all_feeds: list, headers: dict, site: str) -> None:
    # save all feeds to database
    r = requests.post(
        "https://es-indieweb-search.jamesg.blog/save",
        json={"feeds": all_feeds},
        headers=headers,
    )

    if r.status_code == 200:
        # print("feeds updated in database for {}".format(site))
        print(f"feeds updated database for {site}")
    else:
        # print("ERROR: feeds not updated for {} (status code {})".format(site, r.status_code))
        logging.error(f"feeds not updated for {site} (status code {r.status_code})")


def save_indexed_urls_to_database(
    dict_of_urls_and_hashes: list, headers: dict, site: str
) -> None:
    # convert dict_of_urls_and_hashes into list of lists
    list_of_urls_and_hashes = [[i[0], i[1]] for i in dict_of_urls_and_hashes.items()]

    r = requests.post(
        "https://es-indieweb-search.jamesg.blog/finish_crawl",
        json={"url": list_of_urls_and_hashes},
        headers=headers,
    )

    if r.status_code == 200:
        print(f"index list updated for {site}")
    else:
        logging.error(
            f"index list not updates for {site} (status code {r.status_code})"
        )


def record_crawl_of_domain(site: str, headers: dict) -> None:
    del headers["Content-Type"]

    r = requests.post(
        "https://es-indieweb-search.jamesg.blog/create_crawled",
        data={"url": site},
        headers=headers,
    )

    if r.status_code == 200:
        # print(r.text)
        # print("crawl recorded in database for {}".format(site))
        print(f"crawl recorded in database for {site}")
    else:
        # print("ERROR: crawl not recorded in database for {} (status code {})".format(site, r.status_code))
        logging.error(
            f"crawl not recorded in database for {site} (status code {r.status_code})"
        )


def remove_crawl_from_queue(site) -> None:
    with open("crawl_queue.txt", "r") as f:
        rows = f.readlines()

    if site in rows:
        rows.remove(site)

    if site + "\n" in rows:
        rows.remove(site + "\n")

    with open("crawl_queue.txt", "w+") as f:
        f.writelines(rows)
